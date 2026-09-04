"""Repositorios del módulo grupo."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.grupo.domain.grupo import Grupo
from tarjeta.modules.grupo.domain.invitacion import Invitacion
from tarjeta.modules.grupo.domain.miembro import Miembro
from tarjeta.modules.grupo.domain.tipos import (
    EstadoGrupo,
    EstadoInvitacion,
    EstadoMiembro,
    ModoBilletera,
    RolGrupo,
)
from tarjeta.shared.domain.types import EntityId

from .models import AlertaGrupoModel, GrupoModel, InvitacionModel, MiembroModel


def _grupo_to_domain(m: GrupoModel) -> Grupo:
    return Grupo(
        id=EntityId(m.id),
        id_titular=m.id_titular,
        modo_billetera=ModoBilletera(m.modo_billetera),
        estado=EstadoGrupo(m.estado),
        creado_en=m.creado_en,
    )


def _miembro_to_domain(m: MiembroModel) -> Miembro:
    return Miembro(
        id=EntityId(m.id),
        id_grupo=EntityId(m.id_grupo),
        id_persona=m.id_persona,
        rol=RolGrupo(m.rol),
        estado=EstadoMiembro(m.estado),
        fecha_alta=m.fecha_alta,
        tope_mensual=m.tope_mensual,
    )


class SqlAlchemyGrupoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, grupo: Grupo) -> None:
        self._s.add(
            GrupoModel(
                id=grupo.id.value,
                id_titular=grupo.id_titular,
                modo_billetera=grupo.modo_billetera.value,
                estado=grupo.estado.value,
                creado_en=grupo.creado_en,
            )
        )
        await self._s.flush()

    async def guardar(self, grupo: Grupo) -> None:
        m = await self._s.get(GrupoModel, grupo.id.value)
        if m is None:
            return
        m.id_titular = grupo.id_titular
        m.modo_billetera = grupo.modo_billetera.value
        m.estado = grupo.estado.value

    async def obtener(self, id: EntityId) -> Grupo | None:
        m = await self._s.get(GrupoModel, id.value)
        return _grupo_to_domain(m) if m else None

    async def por_titular(self, id_persona: str) -> Grupo | None:
        m = await self._s.scalar(
            select(GrupoModel).where(
                GrupoModel.id_titular == id_persona,
                GrupoModel.estado == EstadoGrupo.ACTIVO.value,
            )
        )
        return _grupo_to_domain(m) if m else None

    async def agregar_miembro(self, miembro: Miembro) -> None:
        self._s.add(
            MiembroModel(
                id=miembro.id.value,
                id_grupo=miembro.id_grupo.value,
                id_persona=miembro.id_persona,
                rol=miembro.rol.value,
                estado=miembro.estado.value,
                fecha_alta=miembro.fecha_alta,
                tope_mensual=miembro.tope_mensual,
            )
        )
        await self._s.flush()

    async def guardar_miembro(self, miembro: Miembro) -> None:
        m = await self._s.get(MiembroModel, miembro.id.value)
        if m is None:
            return
        m.rol = miembro.rol.value
        m.estado = miembro.estado.value
        m.tope_mensual = miembro.tope_mensual

    async def miembro_de(self, id_persona: str) -> Miembro | None:
        # No-baja: un miembro SUSPENDIDO sigue ocupando su grupo (una persona, un grupo) y sigue
        # heredando el nivel; la suspensión solo afecta el gasto del pozo (§10.6).
        m = await self._s.scalar(
            select(MiembroModel).where(
                MiembroModel.id_persona == id_persona,
                MiembroModel.estado != EstadoMiembro.BAJA.value,
            )
        )
        return _miembro_to_domain(m) if m else None

    async def miembro_en(self, id_grupo: EntityId, id_persona: str) -> Miembro | None:
        m = await self._s.scalar(
            select(MiembroModel).where(
                MiembroModel.id_grupo == id_grupo.value,
                MiembroModel.id_persona == id_persona,
                MiembroModel.estado != EstadoMiembro.BAJA.value,
            )
        )
        return _miembro_to_domain(m) if m else None

    async def miembros_activos(self, id_grupo: EntityId) -> list[Miembro]:
        rows = (
            await self._s.execute(
                select(MiembroModel)
                .where(
                    MiembroModel.id_grupo == id_grupo.value,
                    MiembroModel.estado != EstadoMiembro.BAJA.value,
                )
                .order_by(MiembroModel.fecha_alta.asc())
            )
        ).scalars()
        return [_miembro_to_domain(m) for m in rows]


class SqlAlchemyInvitacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, invitacion: Invitacion) -> None:
        self._s.add(
            InvitacionModel(
                id=invitacion.id.value,
                id_grupo=invitacion.id_grupo.value,
                token=invitacion.token,
                texto_declaracion=invitacion.texto_declaracion,
                id_titular=invitacion.id_titular,
                ip_titular=invitacion.ip_titular,
                declarada_en=invitacion.declarada_en,
                vence_en=invitacion.vence_en,
                estado=invitacion.estado.value,
                aceptada_por=invitacion.aceptada_por,
                aceptada_en=invitacion.aceptada_en,
            )
        )
        await self._s.flush()

    async def guardar(self, invitacion: Invitacion) -> None:
        m = await self._s.get(InvitacionModel, invitacion.id.value)
        if m is None:
            return
        m.estado = invitacion.estado.value
        m.aceptada_por = invitacion.aceptada_por
        m.aceptada_en = invitacion.aceptada_en

    async def por_token(self, token: str) -> Invitacion | None:
        m = await self._s.scalar(select(InvitacionModel).where(InvitacionModel.token == token))
        if m is None:
            return None
        return Invitacion(
            id=EntityId(m.id),
            id_grupo=EntityId(m.id_grupo),
            token=m.token,
            texto_declaracion=m.texto_declaracion,
            id_titular=m.id_titular,
            ip_titular=m.ip_titular,
            declarada_en=m.declarada_en,
            vence_en=m.vence_en,
            estado=EstadoInvitacion(m.estado),
            aceptada_por=m.aceptada_por,
            aceptada_en=m.aceptada_en,
        )


class SqlAlchemyAlertaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def registrar(self, *, id_grupo: str, tipo: str, detalle: str) -> None:
        self._s.add(
            AlertaGrupoModel(
                id=uuid.uuid4(),
                id_grupo=id_grupo,
                tipo=tipo,
                detalle=detalle,
                creado_en=datetime.now(UTC),
            )
        )
        await self._s.flush()

    async def de_grupo(self, id_grupo: str) -> list[tuple[str, str, str]]:
        rows = (
            await self._s.execute(
                select(AlertaGrupoModel.tipo, AlertaGrupoModel.detalle, AlertaGrupoModel.creado_en)
                .where(AlertaGrupoModel.id_grupo == id_grupo)
                .order_by(AlertaGrupoModel.creado_en.desc())
            )
        ).all()
        return [(t, d, c.isoformat()) for t, d, c in rows]
