"""Composición del módulo grupo."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.grupo.application.deps import GrupoPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .repositories import (
    SqlAlchemyAlertaRepository,
    SqlAlchemyGrupoRepository,
    SqlAlchemyInvitacionRepository,
)


def construir_puertos_grupo(session: AsyncSession) -> GrupoPuertos:
    return GrupoPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        grupos=SqlAlchemyGrupoRepository(session),
        invitaciones=SqlAlchemyInvitacionRepository(session),
        alertas=SqlAlchemyAlertaRepository(session),
        outbox=SqlAlchemyOutbox(session),
    )
