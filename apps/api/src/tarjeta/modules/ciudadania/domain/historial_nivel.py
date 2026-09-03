"""HistorialNivel: registro append-only con snapshot de la regla aplicada (§1.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tarjeta.shared.domain.types import EntityId


@dataclass(frozen=True, slots=True)
class HistorialNivel:
    id: EntityId
    id_persona: EntityId
    nivel_anterior: str
    nivel_nuevo: str
    motivo: str
    detalle_regla_aplicada: str  # snapshot textual, no una referencia mutable
    timestamp: datetime
