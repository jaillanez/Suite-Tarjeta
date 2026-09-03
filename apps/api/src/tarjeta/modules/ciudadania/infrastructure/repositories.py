"""Repositorios del módulo ciudadania."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.ciudadania.domain.excepcion import ExcepcionNivel
from tarjeta.modules.ciudadania.domain.historial_nivel import HistorialNivel
from tarjeta.modules.ciudadania.domain.nivel import Nivel, NivelOrigen
from tarjeta.modules.ciudadania.domain.perfil_ciudadano import PerfilCiudadano
from tarjeta.modules.ciudadania.domain.tarjeta import EstadoTarjeta
from tarjeta.shared.domain.types import EntityId

from .models import ExcepcionNivelModel, HistorialNivelModel, PerfilCiudadanoModel


class SqlAlchemyPerfilCiudadanoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener(self, id_persona: EntityId) -> PerfilCiudadano | None:
        m = await self._session.get(PerfilCiudadanoModel, id_persona.value)
        if m is None:
            return None
        return PerfilCiudadano.rehidratar(
            id_persona=EntityId(m.id_persona),
            nivel=Nivel(m.nivel),
            nivel_origen=NivelOrigen(m.nivel_origen),
            numero_tarjeta=m.numero_tarjeta,
            estado_tarjeta=EstadoTarjeta(m.estado_tarjeta),
            tiene_tarjeta_fisica=m.tiene_tarjeta_fisica,
            fecha_ultimo_calculo=m.fecha_ultimo_calculo,
        )

    async def agregar(self, perfil: PerfilCiudadano) -> None:
        self._session.add(
            PerfilCiudadanoModel(
                id_persona=perfil.id.value,
                nivel=perfil.nivel.value,
                nivel_origen=perfil.nivel_origen.value,
                numero_tarjeta=perfil.numero_tarjeta,
                estado_tarjeta=perfil.estado_tarjeta.value,
                tiene_tarjeta_fisica=perfil.tiene_tarjeta_fisica,
                fecha_ultimo_calculo=perfil.fecha_ultimo_calculo,
            )
        )

    async def guardar(self, perfil: PerfilCiudadano) -> None:
        m = await self._session.get(PerfilCiudadanoModel, perfil.id.value)
        if m is None:
            return
        m.nivel = perfil.nivel.value
        m.nivel_origen = perfil.nivel_origen.value
        m.numero_tarjeta = perfil.numero_tarjeta
        m.estado_tarjeta = perfil.estado_tarjeta.value
        m.tiene_tarjeta_fisica = perfil.tiene_tarjeta_fisica
        m.fecha_ultimo_calculo = perfil.fecha_ultimo_calculo


class SqlAlchemyHistorialNivelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, historial: HistorialNivel) -> None:
        self._session.add(
            HistorialNivelModel(
                id=historial.id.value,
                id_persona=historial.id_persona.value,
                nivel_anterior=historial.nivel_anterior,
                nivel_nuevo=historial.nivel_nuevo,
                motivo=historial.motivo,
                detalle_regla_aplicada=historial.detalle_regla_aplicada,
                timestamp=historial.timestamp,
            )
        )


class SqlAlchemyExcepcionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, excepcion: ExcepcionNivel) -> None:
        self._session.add(
            ExcepcionNivelModel(
                id=excepcion.id.value,
                id_persona=excepcion.id_persona.value,
                motivo=excepcion.motivo,
                vigencia_desde=excepcion.vigencia_desde,
                vigencia_hasta=excepcion.vigencia_hasta,
            )
        )

    async def hay_black_vigente(self, id_persona: EntityId, ahora: datetime) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        ExcepcionNivelModel.id_persona == id_persona.value,
                        ExcepcionNivelModel.vigencia_desde <= ahora,
                        ExcepcionNivelModel.vigencia_hasta >= ahora,
                    )
                )
            )
        )

    async def listar(self, id_persona: EntityId) -> list[ExcepcionNivel]:
        rows = (
            await self._session.execute(
                select(ExcepcionNivelModel).where(
                    ExcepcionNivelModel.id_persona == id_persona.value
                )
            )
        ).scalars()
        return [
            ExcepcionNivel(
                id=EntityId(m.id),
                id_persona=EntityId(m.id_persona),
                motivo=m.motivo,
                vigencia_desde=m.vigencia_desde,
                vigencia_hasta=m.vigencia_hasta,
            )
            for m in rows
        ]
