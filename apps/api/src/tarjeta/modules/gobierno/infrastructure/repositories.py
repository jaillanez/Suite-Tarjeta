"""Repositorios del módulo gobierno."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import exists, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.gobierno.domain.aprobacion import EstadoSolicitud, SolicitudAprobacion
from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.domain.roles import RolMunicipal
from tarjeta.shared.domain.types import EntityId

from .models import (
    AgenteMunicipalModel,
    ParametroModel,
    RegistroAuditoriaModel,
    SolicitudAprobacionModel,
)


class SqlAlchemyAuditoriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, r: RegistroAuditoria) -> None:
        self._session.add(
            RegistroAuditoriaModel(
                id=r.id.value,
                timestamp=r.timestamp,
                id_persona_actor=r.id_persona_actor,
                rol_actor=r.rol_actor,
                perfil_activo=r.perfil_activo,
                accion=r.accion,
                entidad=r.entidad,
                id_entidad=r.id_entidad,
                valor_anterior=r.valor_anterior,
                valor_nuevo=r.valor_nuevo,
                ip=r.ip,
                user_agent=r.user_agent,
                huella_dispositivo=r.huella_dispositivo,
                motivo=r.motivo,
                id_evento_origen=r.id_evento_origen,
            )
        )

    async def existe_evento(self, id_evento_origen: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(RegistroAuditoriaModel.id_evento_origen == id_evento_origen))
            )
        )

    async def listar(
        self,
        *,
        actor: str | None,
        accion: str | None,
        entidad: str | None,
        limite: int,
        offset: int,
    ) -> list[RegistroAuditoria]:
        q = select(RegistroAuditoriaModel).order_by(RegistroAuditoriaModel.timestamp.desc())
        if actor:
            q = q.where(RegistroAuditoriaModel.id_persona_actor == actor)
        if accion:
            q = q.where(RegistroAuditoriaModel.accion == accion)
        if entidad:
            q = q.where(RegistroAuditoriaModel.entidad == entidad)
        q = q.limit(limite).offset(offset)
        rows = (await self._session.execute(q)).scalars()
        return [
            RegistroAuditoria(
                id=EntityId(m.id),
                timestamp=m.timestamp,
                id_persona_actor=m.id_persona_actor,
                rol_actor=m.rol_actor,
                perfil_activo=m.perfil_activo,
                accion=m.accion,
                entidad=m.entidad,
                id_entidad=m.id_entidad,
                valor_anterior=m.valor_anterior,
                valor_nuevo=m.valor_nuevo,
                ip=m.ip,
                user_agent=m.user_agent,
                huella_dispositivo=m.huella_dispositivo,
                motivo=m.motivo,
                id_evento_origen=m.id_evento_origen,
            )
            for m in rows
        ]


def _to_solicitud(m: SolicitudAprobacionModel) -> SolicitudAprobacion:
    return SolicitudAprobacion(
        id=EntityId(m.id),
        accion=m.accion,
        payload=m.payload,
        id_solicitante=m.id_solicitante,
        rol_solicitante=RolMunicipal(m.rol_solicitante),
        estado=EstadoSolicitud(m.estado),
        fecha_solicitud=m.fecha_solicitud,
        fecha_expiracion=m.fecha_expiracion,
        id_aprobador=m.id_aprobador,
        motivo_decision=m.motivo_decision,
        fecha_decision=m.fecha_decision,
    )


class SqlAlchemyAprobacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, s: SolicitudAprobacion) -> None:
        self._session.add(
            SolicitudAprobacionModel(
                id=s.id.value,
                accion=s.accion,
                payload=s.payload,
                id_solicitante=s.id_solicitante,
                rol_solicitante=s.rol_solicitante.value,
                estado=s.estado.value,
                fecha_solicitud=s.fecha_solicitud,
                fecha_expiracion=s.fecha_expiracion,
            )
        )

    async def obtener(self, id: EntityId) -> SolicitudAprobacion | None:
        m = await self._session.get(SolicitudAprobacionModel, id.value)
        return _to_solicitud(m) if m else None

    async def guardar(self, s: SolicitudAprobacion) -> None:
        m = await self._session.get(SolicitudAprobacionModel, s.id.value)
        if m is None:
            return
        m.estado = s.estado.value
        m.id_aprobador = s.id_aprobador
        m.motivo_decision = s.motivo_decision
        m.fecha_decision = s.fecha_decision

    async def listar_pendientes(self) -> list[SolicitudAprobacion]:
        rows = (
            await self._session.execute(
                select(SolicitudAprobacionModel).where(
                    SolicitudAprobacionModel.estado == EstadoSolicitud.PENDIENTE.value
                )
            )
        ).scalars()
        return [_to_solicitud(m) for m in rows]

    async def expirar_vencidas(self, ahora: datetime) -> int:
        result: Any = await self._session.execute(
            update(SolicitudAprobacionModel)
            .where(
                SolicitudAprobacionModel.estado == EstadoSolicitud.PENDIENTE.value,
                SolicitudAprobacionModel.fecha_expiracion < ahora,
            )
            .values(estado=EstadoSolicitud.EXPIRADA.value)
        )
        return int(result.rowcount or 0)


class SqlAlchemyParametroRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener(self, clave: str) -> int | None:
        valor: int | None = await self._session.scalar(
            select(ParametroModel.valor).where(ParametroModel.clave == clave)
        )
        return valor

    async def todos(self) -> dict[str, int]:
        rows = (await self._session.execute(select(ParametroModel))).scalars()
        return {m.clave: m.valor for m in rows}

    async def guardar(self, clave: str, valor: int) -> None:
        stmt = (
            pg_insert(ParametroModel)
            .values(clave=clave, valor=valor)
            .on_conflict_do_update(index_elements=["clave"], set_={"valor": valor})
        )
        await self._session.execute(stmt)


class SqlAlchemyAgenteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rol_de(self, id_persona: EntityId) -> RolMunicipal | None:
        # Solo agentes activos: si identidad revocó el perfil municipal, no hay acceso.
        rol = await self._session.scalar(
            select(AgenteMunicipalModel.rol).where(
                AgenteMunicipalModel.id_persona == id_persona.value,
                AgenteMunicipalModel.activo.is_(True),
            )
        )
        return RolMunicipal(rol) if rol else None

    async def asignar(self, id_persona: EntityId, rol: RolMunicipal) -> None:
        stmt = (
            pg_insert(AgenteMunicipalModel)
            .values(id_persona=id_persona.value, rol=rol.value, activo=True)
            .on_conflict_do_update(
                index_elements=["id_persona"], set_={"rol": rol.value, "activo": True}
            )
        )
        await self._session.execute(stmt)

    async def desactivar(self, id_persona: EntityId) -> None:
        await self._session.execute(
            update(AgenteMunicipalModel)
            .where(AgenteMunicipalModel.id_persona == id_persona.value)
            .values(activo=False)
        )

    async def listar(self) -> list[tuple[str, RolMunicipal]]:
        rows = (
            await self._session.execute(
                select(AgenteMunicipalModel).where(AgenteMunicipalModel.activo.is_(True))
            )
        ).scalars()
        return [(str(m.id_persona), RolMunicipal(m.rol)) for m in rows]


class SqlAlchemyRecaudacionRepository:
    """Métrica de recaudación (§5.6), de **solo lectura**.

    Lee vistas creadas por migración (`vista_recaudacion_*`) en vez de cruzar tablas de
    otros módulos con SQL directo. Es la excepción declarada en docs/arquitectura.md: solo
    lectura y reportes; si otro módulo cambia su esquema, la vista rompe de forma ruidosa.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def transiciones_a_black_post_registro(self) -> int:
        val = await self._session.scalar(text("SELECT total FROM vista_recaudacion_transiciones"))
        return int(val or 0)

    async def distribucion_por_nivel(self) -> dict[str, int]:
        rows = (
            await self._session.execute(
                text("SELECT nivel, total FROM vista_recaudacion_por_nivel")
            )
        ).all()
        return {str(nivel): int(cnt) for nivel, cnt in rows}
