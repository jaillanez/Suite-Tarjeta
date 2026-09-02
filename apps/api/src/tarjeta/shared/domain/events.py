"""Eventos de dominio.

Un evento describe algo que ya pasó en el dominio. Es inmutable. Los agregados los
acumulan y la capa de aplicación los publica tras confirmar la unidad de trabajo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base de todos los eventos de dominio."""

    event_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

    @property
    def name(self) -> str:
        return type(self).__name__
