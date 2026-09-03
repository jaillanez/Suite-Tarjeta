"""Value objects propios de identidad (Celular, Email)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tarjeta.shared.domain.errors import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Celular:
    """Número de celular normalizado a solo dígitos."""

    value: str

    def __post_init__(self) -> None:
        digits = "".join(ch for ch in self.value if ch.isdigit())
        if not 8 <= len(digits) <= 15:
            raise ValidationError(f"Celular inválido: {self.value!r}")
        object.__setattr__(self, "value", digits)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Email:
    """Correo electrónico, normalizado a minúsculas."""

    value: str

    def __post_init__(self) -> None:
        normalizado = self.value.strip().lower()
        if not _EMAIL_RE.match(normalizado):
            raise ValidationError(f"Email inválido: {self.value!r}")
        object.__setattr__(self, "value", normalizado)

    def __str__(self) -> str:
        return self.value
