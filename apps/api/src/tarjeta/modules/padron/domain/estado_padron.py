"""EstadoPadron: cache del veredicto municipal (§7.5). Sin montos ni cuentas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tarjeta.shared.domain.types import EntityId


@dataclass(slots=True)
class EstadoPadron:
    id_persona: EntityId
    dni: str
    al_dia: bool
    es_comerciante: bool
    fecha_ultima_consulta: datetime
