"""Composición del módulo puntos."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.puntos.application.deps import PuntosConfig, PuntosPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .repositories import (
    SqlAlchemyBilleteraRepository,
    SqlAlchemyComprobanteInventarioRepository,
    SqlAlchemyItemCatalogoRepository,
    SqlAlchemyLoteRepository,
    SqlAlchemyMovimientoRepository,
)


def construir_puertos_puntos(
    session: AsyncSession, config: PuntosConfig | None = None
) -> PuntosPuertos:
    return PuntosPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        billeteras=SqlAlchemyBilleteraRepository(session),
        lotes=SqlAlchemyLoteRepository(session),
        movimientos=SqlAlchemyMovimientoRepository(session),
        catalogo=SqlAlchemyItemCatalogoRepository(session),
        comprobantes=SqlAlchemyComprobanteInventarioRepository(session),
        outbox=SqlAlchemyOutbox(session),
        config=config or PuntosConfig(),
    )
