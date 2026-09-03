"""Perfiles de una persona (§11.2). Una credencial, varios perfiles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tarjeta.shared.domain.types import EntityId


class TipoPerfil(StrEnum):
    CIUDADANO = "CIUDADANO"
    COMERCIO = "COMERCIO"
    MUNICIPAL = "MUNICIPAL"


@dataclass(frozen=True, slots=True)
class Perfil:
    """Un perfil asignado a la persona.

    Para COMERCIO puede haber más de uno (uno por comercio), con su rol. El detalle de
    negocio de cada tipo vive en los módulos ciudadania/comercios/gobierno.
    """

    tipo: TipoPerfil
    id_comercio: EntityId | None = None
    rol: str | None = None

    def clave(self) -> str:
        """Identificador estable del perfil para el selector de contexto."""
        if self.tipo is TipoPerfil.COMERCIO and self.id_comercio is not None:
            return f"COMERCIO:{self.id_comercio}"
        return str(self.tipo)
