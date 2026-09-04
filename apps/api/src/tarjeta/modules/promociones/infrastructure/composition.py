"""Composición del módulo promociones."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.promociones.application.deps import PromocionesPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .repositories import (
    SqlAlchemyFavoritoRepository,
    SqlAlchemyPerfilConfianzaRepository,
    SqlAlchemyPromocionRepository,
)


def construir_puertos_promociones(session: AsyncSession) -> PromocionesPuertos:
    return PromocionesPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        promociones=SqlAlchemyPromocionRepository(session),
        confianza=SqlAlchemyPerfilConfianzaRepository(session),
        favoritos=SqlAlchemyFavoritoRepository(session),
        outbox=SqlAlchemyOutbox(session),
    )
