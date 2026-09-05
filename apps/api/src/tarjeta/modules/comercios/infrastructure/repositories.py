"""Repositorios del módulo comercios (incluye consultas geográficas con PostGIS)."""

from __future__ import annotations

from datetime import time
from typing import Any

from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_Distance, ST_DWithin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.comercios.domain.comercio import (
    ESTADOS_HABILITADOS,
    Comercio,
    EstadoComercio,
    EvidenciaConvenio,
)
from tarjeta.modules.comercios.domain.invitacion import EstadoInvitacion, Invitacion
from tarjeta.modules.comercios.domain.roles import RolComercio
from tarjeta.modules.comercios.domain.sucursal import (
    EstadoSucursal,
    Franja,
    Horario,
    Sucursal,
    SucursalCercana,
)
from tarjeta.modules.comercios.domain.turno import Turno
from tarjeta.modules.comercios.domain.usuario import EstadoUsuario, UsuarioComercio
from tarjeta.shared.domain.types import EntityId

from .models import (
    ComercioModel,
    InvitacionComercioModel,
    SucursalModel,
    TurnoModel,
    UsuarioComercioModel,
)


def _punto(lat: float, lon: float) -> WKTElement:
    # PostGIS espera POINT(lon lat).
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def _horarios_a_json(horarios: list[Horario]) -> list[dict[str, Any]]:
    return [
        {
            "dia": h.dia,
            "franjas": [
                {
                    "desde": f.desde.isoformat(timespec="minutes"),
                    "hasta": f.hasta.isoformat(timespec="minutes"),
                }
                for f in h.franjas
            ],
        }
        for h in horarios
    ]


def _json_a_horarios(data: list[dict[str, Any]]) -> list[Horario]:
    return [
        Horario(
            dia=int(h["dia"]),
            franjas=tuple(
                Franja(desde=time.fromisoformat(f["desde"]), hasta=time.fromisoformat(f["hasta"]))
                for f in h.get("franjas", [])
            ),
        )
        for h in data
    ]


class SqlAlchemyComercioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, c: Comercio) -> ComercioModel:
        return ComercioModel(
            id=c.id.value,
            cuit=c.cuit,
            razon_social=c.razon_social,
            nombre_fantasia=c.nombre_fantasia,
            rubro=c.rubro,
            logo_url=c.logo_url,
            id_responsable=c.id_responsable.value,
            estado=c.estado.value,
            convenio_version=c.convenio.version if c.convenio else None,
            convenio_fecha=c.convenio.fecha if c.convenio else None,
            convenio_ip=c.convenio.ip if c.convenio else None,
            creado_en=c.creado_en,
        )

    def _to_domain(self, m: ComercioModel) -> Comercio:
        convenio = None
        if m.convenio_version is not None and m.convenio_fecha is not None:
            convenio = EvidenciaConvenio(
                version=m.convenio_version, fecha=m.convenio_fecha, ip=m.convenio_ip or ""
            )
        return Comercio(
            id=EntityId(m.id),
            cuit=m.cuit,
            razon_social=m.razon_social,
            nombre_fantasia=m.nombre_fantasia,
            rubro=m.rubro,
            logo_url=m.logo_url,
            id_responsable=EntityId(m.id_responsable),
            estado=EstadoComercio(m.estado),
            convenio=convenio,
            creado_en=m.creado_en,
        )

    async def agregar(self, comercio: Comercio) -> None:
        self._s.add(self._to_model(comercio))
        await self._s.flush()

    async def guardar(self, comercio: Comercio) -> None:
        m = await self._s.get(ComercioModel, comercio.id.value)
        if m is None:
            return
        m.razon_social = comercio.razon_social
        m.nombre_fantasia = comercio.nombre_fantasia
        m.rubro = comercio.rubro
        m.logo_url = comercio.logo_url
        m.estado = comercio.estado.value

    async def obtener(self, id: EntityId) -> Comercio | None:
        m = await self._s.get(ComercioModel, id.value)
        return self._to_domain(m) if m else None

    async def obtener_por_cuit(self, cuit: str) -> Comercio | None:
        m = await self._s.scalar(select(ComercioModel).where(ComercioModel.cuit == cuit))
        return self._to_domain(m) if m else None

    async def listar(self, estados: list[EstadoComercio] | None = None) -> list[Comercio]:
        q = select(ComercioModel).order_by(ComercioModel.creado_en.desc())
        if estados:
            q = q.where(ComercioModel.estado.in_([e.value for e in estados]))
        rows = (await self._s.execute(q)).scalars()
        return [self._to_domain(m) for m in rows]


class SqlAlchemySucursalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, x: Sucursal) -> SucursalModel:
        # §07.0.B: `ubicacion` (geography) es la ÚNICA fuente de verdad; un trigger de base
        # deriva lat/lon de ella. Por eso no se escriben lat/lon acá.
        return SucursalModel(
            id=x.id.value,
            id_comercio=x.id_comercio.value,
            nombre=x.nombre,
            direccion=x.direccion,
            telefono=x.telefono,
            ubicacion=_punto(x.lat, x.lon),
            estado=x.estado.value,
            es_casa_central=x.es_casa_central,
            horarios=_horarios_a_json(x.horarios),
            fotos=list(x.fotos),
            qr_token=x.qr_token,
            motivo_cierre=x.motivo_cierre,
            reapertura_estimada=x.reapertura_estimada,
        )

    def _to_domain(self, m: SucursalModel) -> Sucursal:
        return Sucursal(
            id=EntityId(m.id),
            id_comercio=EntityId(m.id_comercio),
            nombre=m.nombre,
            direccion=m.direccion,
            lat=m.lat,
            lon=m.lon,
            telefono=m.telefono,
            estado=EstadoSucursal(m.estado),
            es_casa_central=m.es_casa_central,
            horarios=_json_a_horarios(m.horarios),
            fotos=list(m.fotos),
            qr_token=m.qr_token,
            motivo_cierre=m.motivo_cierre,
            reapertura_estimada=m.reapertura_estimada,
        )

    async def agregar(self, sucursal: Sucursal) -> None:
        self._s.add(self._to_model(sucursal))
        await self._s.flush()

    async def guardar(self, sucursal: Sucursal) -> None:
        m = await self._s.get(SucursalModel, sucursal.id.value)
        if m is None:
            return
        m.nombre = sucursal.nombre
        m.direccion = sucursal.direccion
        m.telefono = sucursal.telefono
        # §07.0.B: solo se escribe `ubicacion`; el trigger re-deriva lat/lon.
        m.ubicacion = _punto(sucursal.lat, sucursal.lon)
        m.estado = sucursal.estado.value
        m.horarios = _horarios_a_json(sucursal.horarios)
        m.fotos = list(sucursal.fotos)
        m.qr_token = sucursal.qr_token
        m.motivo_cierre = sucursal.motivo_cierre
        m.reapertura_estimada = sucursal.reapertura_estimada

    async def obtener(self, id: EntityId) -> Sucursal | None:
        m = await self._s.get(SucursalModel, id.value)
        return self._to_domain(m) if m else None

    async def listar_por_comercio(self, id_comercio: EntityId) -> list[Sucursal]:
        rows = (
            await self._s.execute(
                select(SucursalModel).where(SucursalModel.id_comercio == id_comercio.value)
            )
        ).scalars()
        return [self._to_domain(m) for m in rows]

    async def cercanas(
        self, *, lat: float, lon: float, radio_m: float, limite: int
    ) -> list[SucursalCercana]:
        ref = _punto(lat, lon)
        dist = ST_Distance(SucursalModel.ubicacion, ref).label("dist")
        # §12.1: solo aparecen sucursales ACTIVAS de comercios APROBADOS/ACTIVOS (no de una
        # solicitud en trámite o de un comercio suspendido).
        habilitados = [e.value for e in ESTADOS_HABILITADOS]
        stmt = (
            select(SucursalModel, dist)
            .join(ComercioModel, ComercioModel.id == SucursalModel.id_comercio)
            .where(ST_DWithin(SucursalModel.ubicacion, ref, radio_m))
            .where(SucursalModel.estado == EstadoSucursal.ACTIVA.value)
            .where(ComercioModel.estado.in_(habilitados))
            .order_by(dist)
            .limit(limite)
        )
        rows = (await self._s.execute(stmt)).all()
        return [
            SucursalCercana(
                id=str(m.id),
                nombre=m.nombre,
                lat=m.lat,
                lon=m.lon,
                distancia_m=float(d),
            )
            for m, d in rows
        ]


class SqlAlchemyUsuarioComercioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, u: UsuarioComercio) -> UsuarioComercioModel:
        return UsuarioComercioModel(
            id=u.id.value,
            id_comercio=u.id_comercio.value,
            id_persona=u.id_persona.value,
            rol=u.rol.value,
            sucursales=[str(s) for s in u.sucursales],
            estado=u.estado.value,
            pin_hash=u.pin_hash,
            huella_dispositivo=u.huella_dispositivo,
            pin_intentos=u.pin_intentos,
            pin_bloqueado_hasta=u.pin_bloqueado_hasta,
        )

    def _to_domain(self, m: UsuarioComercioModel) -> UsuarioComercio:
        return UsuarioComercio(
            id=EntityId(m.id),
            id_comercio=EntityId(m.id_comercio),
            id_persona=EntityId(m.id_persona),
            rol=RolComercio(m.rol),
            sucursales=[EntityId.from_str(s) for s in m.sucursales],
            estado=EstadoUsuario(m.estado),
            pin_hash=m.pin_hash,
            huella_dispositivo=m.huella_dispositivo,
            pin_intentos=m.pin_intentos,
            pin_bloqueado_hasta=m.pin_bloqueado_hasta,
        )

    async def agregar(self, usuario: UsuarioComercio) -> None:
        self._s.add(self._to_model(usuario))
        await self._s.flush()

    async def guardar(self, usuario: UsuarioComercio) -> None:
        m = await self._s.get(UsuarioComercioModel, usuario.id.value)
        if m is None:
            return
        m.rol = usuario.rol.value
        m.sucursales = [str(s) for s in usuario.sucursales]
        m.estado = usuario.estado.value
        m.pin_hash = usuario.pin_hash
        m.huella_dispositivo = usuario.huella_dispositivo
        m.pin_intentos = usuario.pin_intentos
        m.pin_bloqueado_hasta = usuario.pin_bloqueado_hasta

    async def obtener(self, id: EntityId) -> UsuarioComercio | None:
        m = await self._s.get(UsuarioComercioModel, id.value)
        return self._to_domain(m) if m else None

    async def obtener_por_persona_y_comercio(
        self, id_persona: EntityId, id_comercio: EntityId
    ) -> UsuarioComercio | None:
        m = await self._s.scalar(
            select(UsuarioComercioModel).where(
                UsuarioComercioModel.id_persona == id_persona.value,
                UsuarioComercioModel.id_comercio == id_comercio.value,
            )
        )
        return self._to_domain(m) if m else None

    async def listar_por_comercio(self, id_comercio: EntityId) -> list[UsuarioComercio]:
        rows = (
            await self._s.execute(
                select(UsuarioComercioModel).where(
                    UsuarioComercioModel.id_comercio == id_comercio.value
                )
            )
        ).scalars()
        return [self._to_domain(m) for m in rows]

    async def listar_por_huella(self, huella: str) -> list[UsuarioComercio]:
        # Cajeros cuyo PIN está atado a este dispositivo (§06.5): el ingreso de caja los
        # identifica por la huella y solo pide el PIN, sin tipear el id de usuario.
        rows = (
            await self._s.execute(
                select(UsuarioComercioModel).where(
                    UsuarioComercioModel.huella_dispositivo == huella
                )
            )
        ).scalars()
        return [self._to_domain(m) for m in rows]


class SqlAlchemyInvitacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, invitacion: Invitacion) -> None:
        self._s.add(
            InvitacionComercioModel(
                id=invitacion.id.value,
                id_comercio=invitacion.id_comercio.value,
                rol=invitacion.rol.value,
                sucursales=[str(s) for s in invitacion.sucursales],
                destino=invitacion.destino,
                token_hash=invitacion.token_hash,
                estado=invitacion.estado.value,
                vence_en=invitacion.vence_en,
            )
        )
        await self._s.flush()

    async def guardar(self, invitacion: Invitacion) -> None:
        m = await self._s.get(InvitacionComercioModel, invitacion.id.value)
        if m is None:
            return
        m.estado = invitacion.estado.value

    async def obtener_por_token_hash(self, token_hash: str) -> Invitacion | None:
        m = await self._s.scalar(
            select(InvitacionComercioModel).where(InvitacionComercioModel.token_hash == token_hash)
        )
        if m is None:
            return None
        return Invitacion(
            id=EntityId(m.id),
            id_comercio=EntityId(m.id_comercio),
            rol=RolComercio(m.rol),
            sucursales=[EntityId.from_str(s) for s in m.sucursales],
            destino=m.destino,
            token_hash=m.token_hash,
            estado=EstadoInvitacion(m.estado),
            vence_en=m.vence_en,
        )


class SqlAlchemyTurnoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, turno: Turno) -> None:
        self._s.add(
            TurnoModel(
                id=turno.id.value,
                id_sucursal=turno.id_sucursal.value,
                id_cajero=turno.id_cajero.value,
                abierto_en=turno.abierto_en,
                cerrado_en=turno.cerrado_en,
                resumen=turno.resumen,
            )
        )
        await self._s.flush()

    async def guardar(self, turno: Turno) -> None:
        m = await self._s.get(TurnoModel, turno.id.value)
        if m is None:
            return
        m.cerrado_en = turno.cerrado_en
        m.resumen = turno.resumen

    async def turno_abierto_de(self, id_cajero: EntityId) -> Turno | None:
        m = await self._s.scalar(
            select(TurnoModel).where(
                TurnoModel.id_cajero == id_cajero.value,
                TurnoModel.cerrado_en.is_(None),
            )
        )
        if m is None:
            return None
        return Turno(
            id=EntityId(m.id),
            id_sucursal=EntityId(m.id_sucursal),
            id_cajero=EntityId(m.id_cajero),
            abierto_en=m.abierto_en,
            cerrado_en=m.cerrado_en,
            resumen=m.resumen,
        )
