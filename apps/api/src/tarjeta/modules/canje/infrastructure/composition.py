"""Composición del módulo canje."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.canje.application.deps import CanjePuertos
from tarjeta.modules.canje.domain.ports import ReservaPromocion
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .repositories import SqlAlchemyComprobanteSecuencia, SqlAlchemyTransaccionRepository


def construir_puertos_canje(session: AsyncSession, reserva: ReservaPromocion) -> CanjePuertos:
    # `reserva` la implementa el composition root con `promociones` (independencia de módulos).
    return CanjePuertos(
        uow=SqlAlchemyUnitOfWork(session),
        transacciones=SqlAlchemyTransaccionRepository(session),
        secuencia=SqlAlchemyComprobanteSecuencia(session),
        reserva=reserva,
        outbox=SqlAlchemyOutbox(session),
    )
