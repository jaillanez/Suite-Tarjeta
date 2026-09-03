"""RegistroAuditoria: registro inmutable (append-only) de acciones (§05.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tarjeta.shared.domain.types import EntityId


@dataclass(frozen=True, slots=True)
class RegistroAuditoria:
    id: EntityId
    timestamp: datetime
    accion: str
    entidad: str
    id_entidad: str
    id_persona_actor: str | None = None
    rol_actor: str | None = None
    perfil_activo: str | None = None
    valor_anterior: dict[str, Any] = field(default_factory=dict)
    valor_nuevo: dict[str, Any] = field(default_factory=dict)
    ip: str = ""
    user_agent: str = ""
    huella_dispositivo: str | None = None
    motivo: str = ""
    id_evento_origen: str | None = None

    @classmethod
    def crear(cls, **kwargs: Any) -> RegistroAuditoria:
        kwargs.setdefault("id", EntityId.new())
        kwargs.setdefault("timestamp", datetime.now(UTC))
        return cls(**kwargs)
