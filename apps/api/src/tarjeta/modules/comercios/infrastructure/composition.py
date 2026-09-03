"""Composición del módulo comercios."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.comercios.application.deps import ComerciosPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .firma import FirmadorEstablecimientoHmac
from .pin import Argon2PinHasher
from .repositories import (
    SqlAlchemyComercioRepository,
    SqlAlchemyInvitacionRepository,
    SqlAlchemySucursalRepository,
    SqlAlchemyTurnoRepository,
    SqlAlchemyUsuarioComercioRepository,
)


def construir_puertos_comercios(session: AsyncSession, settings: Settings) -> ComerciosPuertos:
    return ComerciosPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        comercios=SqlAlchemyComercioRepository(session),
        sucursales=SqlAlchemySucursalRepository(session),
        usuarios=SqlAlchemyUsuarioComercioRepository(session),
        invitaciones=SqlAlchemyInvitacionRepository(session),
        turnos=SqlAlchemyTurnoRepository(session),
        hasher_pin=Argon2PinHasher(),
        firmador=FirmadorEstablecimientoHmac(settings.jwt_secret.get_secret_value()),
        outbox=SqlAlchemyOutbox(session),
    )
