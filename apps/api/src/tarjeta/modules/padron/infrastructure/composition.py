"""Composición del módulo padron."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.padron.application.deps import PadronPuertos
from tarjeta.modules.padron.domain.ports import ClientePadron
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .cliente_real import ClientePadronReal
from .cliente_simulacion import ClientePadronSimulado
from .repositories import SqlAlchemyEstadoPadronRepository


def construir_cliente(settings: Settings) -> ClientePadron:
    # Selección por configuración, no por código (§04.2).
    if settings.padron_modo == "real":
        return ClientePadronReal(
            base_url=settings.padron_base_url,
            api_key=settings.padron_api_key.get_secret_value(),
            timeout=settings.padron_timeout_seconds,
        )
    return ClientePadronSimulado.desde_archivo(settings.padron_sim_archivo)


def construir_puertos_padron(session: AsyncSession, settings: Settings) -> PadronPuertos:
    cipher = FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )
    return PadronPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        repo=SqlAlchemyEstadoPadronRepository(session, cipher=cipher),
        cliente=construir_cliente(settings),
        outbox=SqlAlchemyOutbox(session),
    )
