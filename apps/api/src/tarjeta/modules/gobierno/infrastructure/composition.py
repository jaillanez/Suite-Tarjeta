"""Composición del módulo gobierno."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.gobierno.application.deps import GobiernoPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork

from .repositories import (
    SqlAlchemyAgenteRepository,
    SqlAlchemyAprobacionRepository,
    SqlAlchemyAuditoriaRepository,
    SqlAlchemyParametroRepository,
    SqlAlchemyRecaudacionRepository,
)


def construir_puertos_gobierno(session: AsyncSession) -> GobiernoPuertos:
    return GobiernoPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        auditoria=SqlAlchemyAuditoriaRepository(session),
        aprobaciones=SqlAlchemyAprobacionRepository(session),
        parametros=SqlAlchemyParametroRepository(session),
        agentes=SqlAlchemyAgenteRepository(session),
        recaudacion=SqlAlchemyRecaudacionRepository(session),
    )
