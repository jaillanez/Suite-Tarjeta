"""Excepción de nivel (§5.2): otorga Black con vigencia y motivo; expira sola."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tarjeta.shared.domain.types import EntityId


@dataclass(frozen=True, slots=True)
class ExcepcionNivel:
    id: EntityId
    id_persona: EntityId
    motivo: str
    vigencia_desde: datetime
    vigencia_hasta: datetime

    def vigente(self, ahora: datetime) -> bool:
        return self.vigencia_desde <= ahora <= self.vigencia_hasta
