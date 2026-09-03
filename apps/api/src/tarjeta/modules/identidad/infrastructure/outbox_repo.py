"""Escritura y drenaje del outbox de eventos de dominio (§03.12)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.shared.domain.events import DomainEvent

from .models import OutboxModel

_log = logging.getLogger("identidad.outbox")


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SqlAlchemyOutbox:
    """Persiste los eventos en la misma transacción que el cambio de estado."""

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


async def drenar_outbox(session: AsyncSession) -> int:
    """Consumidor mínimo: escribe los eventos pendientes al log estructurado.

    El consumidor definitivo (auditoría inmutable) llega con el módulo `gobierno`.
    """
    rows = list(
        (
            await session.execute(select(OutboxModel).where(OutboxModel.procesado.is_(False)))
        ).scalars()
    )
    for row in rows:
        _log.info("evento_dominio tipo=%s payload=%s", row.tipo, row.payload)
    if rows:
        await session.execute(
            update(OutboxModel)
            .where(OutboxModel.id.in_([r.id for r in rows]))
            .values(procesado=True)
        )
        await session.commit()
    return len(rows)
