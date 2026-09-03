"""Outbox de eventos de dominio (compartido) y dispatcher entre módulos.

El outbox vive en el shared kernel para que cualquier módulo lo use sin importar a otro
(regla de independencia de módulos). Los eventos se persisten en la misma transacción que
el cambio de estado; el dispatcher los entrega a los handlers suscriptos por nombre.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import DateTime, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.infrastructure.database import Base

_log = logging.getLogger("outbox")


class OutboxModel(Base):
    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    procesado: Mapped[bool] = mapped_column(default=False, index=True)


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SqlAlchemyOutbox:
    """Persiste eventos en la misma transacción que el cambio de estado."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def escribir(self, eventos: list[DomainEvent]) -> None:
        for evento in eventos:
            payload = {k: _json_safe(v) for k, v in asdict(evento).items()}
            self._session.add(
                OutboxModel(
                    id=uuid.uuid4(),
                    tipo=evento.name,
                    payload=payload,
                    ocurrido_en=evento.occurred_at,
                    procesado=False,
                )
            )


# Un handler recibe el payload del evento y la sesión activa; puede escribir nuevos eventos.
Handler = Callable[[dict[str, Any], AsyncSession], Awaitable[None]]


class EventDispatcher:
    """Entrega los eventos del outbox a los handlers suscriptos por nombre.

    Procesa en cadena: un handler puede emitir nuevos eventos que se procesan en la misma
    corrida. También escribe cada evento al log (consumidor mínimo de auditoría).
    """

    _MAX_ITER = 20

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, tipo: str, handler: Handler) -> None:
        self._handlers.setdefault(tipo, []).append(handler)

    async def drain(self, session: AsyncSession) -> int:
        total = 0
        for _ in range(self._MAX_ITER):
            rows = list(
                (
                    await session.execute(
                        select(OutboxModel)
                        .where(OutboxModel.procesado.is_(False))
                        .order_by(OutboxModel.ocurrido_en)
                    )
                ).scalars()
            )
            if not rows:
                break
            for row in rows:
                _log.info("evento_dominio tipo=%s payload=%s", row.tipo, row.payload)
                for handler in self._handlers.get(row.tipo, []):
                    await handler(row.payload, session)
                row.procesado = True
            await session.commit()
            total += len(rows)
        return total
