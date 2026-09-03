"""Composition root de eventos entre módulos (PASO 04).

No es un módulo de dominio: es el lugar donde se cablean los handlers del dispatcher.
Por eso puede importar varios módulos (los módulos entre sí siguen sin importarse).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.ciudadania.application import handlers as ciudadania
from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyExcepcionRepository,
    SqlAlchemyHistorialNivelRepository,
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.gobierno.application.auditoria_consumer import consumir_evento
from tarjeta.modules.gobierno.application.sync_agente import desactivar_agente
from tarjeta.modules.padron.application import consultar as padron
from tarjeta.modules.padron.infrastructure.composition import construir_cliente
from tarjeta.modules.padron.infrastructure.repositories import SqlAlchemyEstadoPadronRepository
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.outbox import EventDispatcher, SqlAlchemyOutbox


def build_dispatcher(settings: Settings) -> EventDispatcher:
    cipher = FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )
    cliente = construir_cliente(settings)

    async def on_identidad_verificada(payload: dict[str, Any], session: AsyncSession) -> None:
        id_persona = EntityId.from_str(str(payload["id_persona"]))
        dni = str(payload["dni"])
        outbox = SqlAlchemyOutbox(session)
        # padron: consulta el veredicto por DNI y emite EstadoPadronActualizado.
        await padron.consultar_y_actualizar(
            repo=SqlAlchemyEstadoPadronRepository(session, cipher=cipher),
            cliente=cliente,
            outbox=outbox,
            id_persona=id_persona,
            dni=dni,
            origen=padron.REGISTRO,
        )
        # ciudadania: crea el PerfilCiudadano (Platino base) y emite la tarjeta.
        await ciudadania.crear_perfil_al_verificar(
            perfiles=SqlAlchemyPerfilCiudadanoRepository(session),
            outbox=outbox,
            id_persona=id_persona,
        )

    async def on_estado_padron_actualizado(payload: dict[str, Any], session: AsyncSession) -> None:
        await ciudadania.recalcular_nivel(
            perfiles=SqlAlchemyPerfilCiudadanoRepository(session),
            historial=SqlAlchemyHistorialNivelRepository(session),
            excepciones=SqlAlchemyExcepcionRepository(session),
            outbox=SqlAlchemyOutbox(session),
            id_persona=EntityId.from_str(str(payload["id_persona"])),
            al_dia=bool(payload["al_dia"]),
            motivo="cálculo automático",
        )

    async def on_solicitud_actualizar(payload: dict[str, Any], session: AsyncSession) -> None:
        await padron.reconsultar(
            repo=SqlAlchemyEstadoPadronRepository(session, cipher=cipher),
            cliente=cliente,
            outbox=SqlAlchemyOutbox(session),
            id_persona=EntityId.from_str(str(payload["id_persona"])),
        )

    dispatcher = EventDispatcher()
    # Auditoría inmutable: consume todos los eventos (§05.4).
    dispatcher.subscribe_all(consumir_evento)
    dispatcher.subscribe("IdentidadVerificada", on_identidad_verificada)
    dispatcher.subscribe("EstadoPadronActualizado", on_estado_padron_actualizado)
    dispatcher.subscribe("SolicitudActualizarEstado", on_solicitud_actualizar)
    # §06.0.B: revocar el perfil municipal en identidad desactiva al agente en gobierno.
    dispatcher.subscribe("PerfilMunicipalRevocado", desactivar_agente)
    return dispatcher
