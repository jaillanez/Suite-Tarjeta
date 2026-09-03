"""Outbox de eventos de dominio (compartido), dispatcher y worker de segundo plano.

El outbox vive en el shared kernel para que cualquier módulo lo use sin importar a otro.
Los eventos se persisten en la misma transacción que el cambio de estado. El dispatcher los
entrega a los handlers; cada evento se procesa en su propia transacción, con reintentos con
retroceso exponencial y una cola de muertos. Un worker de segundo plano drena periódicamente
(no depende del tráfico HTTP).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.infrastructure.database import Base

_log = logging.getLogger("outbox")

MAX_INTENTOS = 5


class OutboxModel(Base):
    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    procesado: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    proximo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    muerto: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


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


Handler = Callable[[dict[str, Any], AsyncSession], Awaitable[None]]


class EventDispatcher:
    """Entrega los eventos del outbox a los handlers. Cada evento en su propia transacción."""

    _MAX_EVENTOS = 200

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}
        self._globales: list[Handler] = []

    def subscribe(self, tipo: str, handler: Handler) -> None:
        self._handlers.setdefault(tipo, []).append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Handler que recibe todos los eventos (p. ej. auditoría)."""
        self._globales.append(handler)

    async def _siguiente(self, session: AsyncSession) -> OutboxModel | None:
        ahora = datetime.now(UTC)
        return (
            await session.execute(
                select(OutboxModel)
                .where(
                    OutboxModel.procesado.is_(False),
                    OutboxModel.muerto.is_(False),
                    (OutboxModel.proximo_intento.is_(None))
                    | (OutboxModel.proximo_intento <= ahora),
                )
                .order_by(OutboxModel.ocurrido_en)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()

    async def drain(self, session: AsyncSession) -> int:
        procesados = 0
        for _ in range(self._MAX_EVENTOS):
            row = await self._siguiente(session)
            if row is None:
                break
            evento_id = row.id
            tipo = row.tipo
            payload = {**row.payload, "__tipo__": tipo}
            try:
                for handler in [*self._globales, *self._handlers.get(tipo, [])]:
                    await handler(payload, session)
                row.procesado = True
                await session.commit()
                procesados += 1
            except Exception as exc:  # noqa: BLE001 - reintento controlado
                await session.rollback()
                fila = await session.get(OutboxModel, evento_id)
                if fila is None:
                    continue
                fila.intentos += 1
                if fila.intentos >= MAX_INTENTOS:
                    fila.muerto = True
                    fila.error = str(exc)
                    _log.error("evento %s a la cola de muertos: %s", tipo, exc)
                else:
                    fila.proximo_intento = datetime.now(UTC) + timedelta(
                        seconds=min(300, 2**fila.intentos)
                    )
                await session.commit()
        return procesados


async def run_worker(
    sessionmaker: async_sessionmaker[AsyncSession],
    dispatcher: EventDispatcher,
    *,
    intervalo_seg: float = 5.0,
    stop: asyncio.Event | None = None,
) -> None:
    """Drena el outbox periódicamente (independiente del tráfico HTTP)."""
    while stop is None or not stop.is_set():
        try:
            async with sessionmaker() as session:
                await dispatcher.drain(session)
        except Exception:  # noqa: BLE001 - el worker nunca muere por un error puntual
            _log.exception("Fallo en el worker de outbox")
        if stop is None:
            await asyncio.sleep(intervalo_seg)
        else:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=intervalo_seg)
