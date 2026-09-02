"""Value objects transversales del dominio.

Incluye identidad (`EntityId`), documentos argentinos con validación real
(`Dni`, `Cuil`), y unidades del negocio (`Dinero`, `Porcentaje`).

Python puro: sin SQLAlchemy, sin Pydantic, sin FastAPI.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from tarjeta.shared.domain.errors import ValidationError

# Pesos del algoritmo de verificación de CUIT/CUIL (módulo 11).
_CUIL_WEIGHTS: tuple[int, ...] = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


@dataclass(frozen=True, slots=True)
class EntityId:
    """Identidad de una entidad. Respaldada por UUIDv7 (ordenable por tiempo)."""

    value: uuid.UUID

    @classmethod
    def new(cls) -> EntityId:
        # uuid7 está disponible de forma nativa en Python 3.14 y coincide con uuidv7() de PG 18.
        return cls(uuid.uuid7())

    @classmethod
    def from_str(cls, raw: str) -> EntityId:
        try:
            return cls(uuid.UUID(raw))
        except ValueError as exc:  # pragma: no cover - defensivo
            raise ValidationError(f"UUID inválido: {raw!r}") from exc

    def __str__(self) -> str:
        return str(self.value)


def _solo_digitos(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def cuil_check_digit(first_ten: str) -> int:
    """Dígito verificador esperado para los primeros 10 dígitos de un CUIT/CUIL.

    Puede devolver 10, que indica un número inválido (ningún CUIL termina en 10).
    """
    total = sum(int(d) * w for d, w in zip(first_ten, _CUIL_WEIGHTS, strict=True))
    return (11 - (total % 11)) % 11


@dataclass(frozen=True, slots=True)
class Dni:
    """Documento Nacional de Identidad. Sin dígito verificador: se valida forma."""

    value: str

    def __post_init__(self) -> None:
        digits = _solo_digitos(self.value)
        if digits != self.value:
            raise ValidationError(f"El DNI debe contener solo dígitos: {self.value!r}")
        if not 7 <= len(digits) <= 8:
            raise ValidationError(f"El DNI debe tener 7 u 8 dígitos: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Cuil:
    """CUIL/CUIT argentino (11 dígitos) con verificación de dígito por módulo 11."""

    value: str

    def __post_init__(self) -> None:
        digits = _solo_digitos(self.value)
        if len(digits) != 11:
            raise ValidationError(f"El CUIL debe tener 11 dígitos: {self.value!r}")
        # Normaliza a solo dígitos (acepta formatos con guiones en la entrada).
        object.__setattr__(self, "value", digits)
        esperado = cuil_check_digit(digits[:10])
        if esperado != int(digits[10]):
            raise ValidationError(f"Dígito verificador de CUIL inválido: {self.value!r}")

    @property
    def dni(self) -> Dni:
        """Los 8 dígitos centrales del CUIL corresponden al DNI."""
        return Dni(str(int(self.value[2:10])))

    def formatted(self) -> str:
        return f"{self.value[:2]}-{self.value[2:10]}-{self.value[10]}"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Dinero:
    """Monto monetario en centavos (entero) para evitar errores de punto flotante."""

    centavos: int

    def __post_init__(self) -> None:
        if not isinstance(self.centavos, int):  # pragma: no cover - defensivo
            raise ValidationError("El monto debe expresarse en centavos enteros")

    @classmethod
    def from_pesos(cls, pesos: Decimal | int | str) -> Dinero:
        return cls(int((Decimal(pesos) * 100).to_integral_value()))

    @property
    def pesos(self) -> Decimal:
        return Decimal(self.centavos) / 100

    def __str__(self) -> str:
        return f"${self.pesos:.2f}"


@dataclass(frozen=True, slots=True)
class Porcentaje:
    """Porcentaje en el rango [0, 100]. El comercio fija el valor libremente."""

    valor: Decimal

    def __post_init__(self) -> None:
        if not 0 <= self.valor <= 100:
            raise ValidationError(f"El porcentaje debe estar entre 0 y 100: {self.valor}")

    @classmethod
    def of(cls, valor: Decimal | int | str) -> Porcentaje:
        return cls(Decimal(valor))

    def fraccion(self) -> Decimal:
        return self.valor / 100

    def __str__(self) -> str:
        return f"{self.valor}%"
