"""Composition root de eventos entre módulos (PASO 04).

No es un módulo de dominio: es el lugar donde se cablean los handlers del dispatcher.
Por eso puede importar varios módulos (los módulos entre sí siguen sin importarse).
"""

from __future__ import annotations

from datetime import UTC, datetime
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
from tarjeta.modules.puntos.application.deps import PuntosConfig
from tarjeta.modules.puntos.application.municipales import AcreditarPuntosMunicipales
from tarjeta.modules.puntos.infrastructure.composition import construir_puertos_puntos
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

    async def on_estado_padron_para_puntos(payload: dict[str, Any], session: AsyncSession) -> None:
        # §09.5: PM por estar al día. Idempotente por período: no confirma la transacción (el
        # dispatcher es dueño de la unidad de trabajo y confirma al final).
        if not bool(payload.get("al_dia")):
            return
        cfg = PuntosConfig(
            vencimiento_meses=settings.puntos_vencimiento_meses,
            base_por_cien=settings.puntos_base_por_cien,
            valor_punto=settings.puntos_valor_peso,
            pm_al_dia=settings.pm_al_dia,
        )
        periodo = datetime.now(UTC).strftime("%Y-%m")
        await AcreditarPuntosMunicipales(construir_puertos_puntos(session, cfg)).acreditar_al_dia(
            id_persona=str(payload["id_persona"]), periodo=periodo
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
    dispatcher.subscribe("EstadoPadronActualizado", on_estado_padron_para_puntos)
    dispatcher.subscribe("SolicitudActualizarEstado", on_solicitud_actualizar)
    # §06.0.B: revocar el perfil municipal en identidad desactiva al agente en gobierno.
    dispatcher.subscribe("PerfilMunicipalRevocado", desactivar_agente)
    return dispatcher
