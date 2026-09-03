"""Router del módulo comercios (portal del comercio + consultas públicas)."""

from __future__ import annotations

from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from tarjeta.modules.comercios.application.cajero import GestionCajero
from tarjeta.modules.comercios.application.sucursales import GestionSucursales
from tarjeta.modules.comercios.application.usuarios import GestionUsuarios
from tarjeta.modules.comercios.domain.roles import Permiso
from tarjeta.modules.comercios.domain.sucursal import Franja, Horario
from tarjeta.modules.comercios.infrastructure.pdf import pdf_establecimiento
from tarjeta.shared.api.auth import HuellaDep
from tarjeta.shared.api.dependencies import SettingsDep
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import ActorComercio, ActorComercioDep, ComerciosPuertosDep, requiere_comercio
from .schemas import (
    AbiertoOut,
    AbrirTurnoIn,
    CierreTemporalIn,
    CierreTurnoOut,
    ComercioOut,
    InvitacionOut,
    InvitarIn,
    Mensaje,
    PinIn,
    SucursalCercanaOut,
    SucursalIn,
    SucursalOut,
    TurnoOut,
    UsuarioComercioOut,
)

router = APIRouter(prefix="/api/v1/comercios", tags=["comercios"])


def _horarios(body: SucursalIn) -> list[Horario]:
    return [
        Horario(
            dia=h.dia,
            franjas=tuple(
                Franja(desde=time.fromisoformat(f.desde), hasta=time.fromisoformat(f.hasta))
                for f in h.franjas
            ),
        )
        for h in body.horarios
    ]


# --------------------------------------------------------------- perfil del comercio


@router.get("/mi-comercio", response_model=ComercioOut)
async def mi_comercio(actor: ActorComercioDep, puertos: ComerciosPuertosDep) -> ComercioOut:
    c = await puertos.comercios.obtener(actor.id_comercio)
    if c is None:
        raise NotFoundError("Comercio inexistente.")
    return ComercioOut(
        id=str(c.id),
        cuit=c.cuit,
        razon_social=c.razon_social,
        nombre_fantasia=c.nombre_fantasia,
        rubro=c.rubro,
        logo_url=c.logo_url,
        estado=c.estado.value,
    )


# --------------------------------------------------------------- sucursales


@router.post("/sucursales", response_model=Mensaje)
async def crear_sucursal(
    body: SucursalIn,
    puertos: ComerciosPuertosDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.SUCURSAL_GESTIONAR))],
) -> Mensaje:
    id_sucursal = await GestionSucursales(puertos).crear(
        id_comercio=str(actor.id_comercio),
        nombre=body.nombre,
        direccion=body.direccion,
        lat=body.lat,
        lon=body.lon,
        telefono=body.telefono,
        es_casa_central=body.es_casa_central,
        horarios=_horarios(body),
        fotos=body.fotos,
    )
    return Mensaje(mensaje=id_sucursal)


@router.get("/sucursales", response_model=list[SucursalOut])
async def listar_sucursales(
    actor: ActorComercioDep, puertos: ComerciosPuertosDep
) -> list[SucursalOut]:
    sucursales = await puertos.sucursales.listar_por_comercio(actor.id_comercio)
    return [
        SucursalOut(
            id=str(s.id),
            id_comercio=str(s.id_comercio),
            nombre=s.nombre,
            direccion=s.direccion,
            telefono=s.telefono,
            lat=s.lat,
            lon=s.lon,
            estado=s.estado.value,
            es_casa_central=s.es_casa_central,
            fotos=list(s.fotos),
            qr_token=s.qr_token,
        )
        for s in sucursales
    ]


@router.post("/sucursales/{id_sucursal}/cerrar-temporal", response_model=Mensaje)
async def cerrar_temporal(
    id_sucursal: str,
    body: CierreTemporalIn,
    puertos: ComerciosPuertosDep,
    _: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.SUCURSAL_GESTIONAR))],
) -> Mensaje:
    await GestionSucursales(puertos).cerrar_temporal(
        id_sucursal, body.motivo, body.reapertura_estimada
    )
    return Mensaje(mensaje="Sucursal cerrada temporalmente.")


@router.post("/sucursales/{id_sucursal}/reabrir", response_model=Mensaje)
async def reabrir(
    id_sucursal: str,
    puertos: ComerciosPuertosDep,
    _: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.SUCURSAL_GESTIONAR))],
) -> Mensaje:
    await GestionSucursales(puertos).reabrir(id_sucursal)
    return Mensaje(mensaje="Sucursal reabierta.")


@router.get("/sucursales/{id_sucursal}/qr.pdf")
async def qr_pdf(
    id_sucursal: str, actor: ActorComercioDep, puertos: ComerciosPuertosDep
) -> Response:
    sucursal = await puertos.sucursales.obtener(EntityId.from_str(id_sucursal))
    if sucursal is None or sucursal.id_comercio != actor.id_comercio:
        raise NotFoundError("Sucursal inexistente.")
    comercio = await puertos.comercios.obtener(actor.id_comercio)
    nombre_comercio = comercio.nombre_fantasia or comercio.razon_social if comercio else ""
    pdf = pdf_establecimiento(
        contenido_qr=sucursal.qr_token, titulo=nombre_comercio, subtitulo=sucursal.nombre
    )
    return Response(content=pdf, media_type="application/pdf")


# --------------------------------------------------------------- consultas públicas


@router.get("/cercanas", response_model=list[SucursalCercanaOut])
async def cercanas(
    puertos: ComerciosPuertosDep,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radio_m: float = Query(5000, gt=0, le=50000),
    limite: int = Query(20, ge=1, le=100),
) -> list[SucursalCercanaOut]:
    resultados = await GestionSucursales(puertos).cercanas(
        lat=lat, lon=lon, radio_m=radio_m, limite=limite
    )
    return [
        SucursalCercanaOut(
            id=r.id, nombre=r.nombre, lat=r.lat, lon=r.lon, distancia_m=round(r.distancia_m, 1)
        )
        for r in resultados
    ]


@router.get("/sucursales/{id_sucursal}/abierto-ahora", response_model=AbiertoOut)
async def abierto_ahora(
    id_sucursal: str, puertos: ComerciosPuertosDep, settings: SettingsDep
) -> AbiertoOut:
    abierto = await GestionSucursales(puertos).abierto_ahora(
        id_sucursal, zona=settings.municipio_timezone
    )
    return AbiertoOut(abierto=abierto)


# --------------------------------------------------------------- usuarios


@router.post("/usuarios/invitar", response_model=InvitacionOut)
async def invitar_usuario(
    body: InvitarIn,
    puertos: ComerciosPuertosDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.USUARIO_GESTIONAR))],
) -> InvitacionOut:
    creada = await GestionUsuarios(puertos).invitar(
        id_comercio=str(actor.id_comercio),
        rol=body.rol,
        destino=body.destino,
        sucursales=body.sucursales,
    )
    return InvitacionOut(id=creada.id_invitacion, token=creada.token)


@router.get("/usuarios", response_model=list[UsuarioComercioOut])
async def listar_usuarios(
    puertos: ComerciosPuertosDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.USUARIO_GESTIONAR))],
) -> list[UsuarioComercioOut]:
    usuarios = await puertos.usuarios.listar_por_comercio(actor.id_comercio)
    return [
        UsuarioComercioOut(
            id=str(u.id),
            id_persona=str(u.id_persona),
            rol=u.rol.value,
            sucursales=[str(s) for s in u.sucursales],
            estado=u.estado.value,
        )
        for u in usuarios
    ]


# --------------------------------------------------------------- cajero y turnos


@router.post("/cajeros/{id_usuario}/pin", response_model=Mensaje)
async def establecer_pin(
    id_usuario: str,
    body: PinIn,
    huella: HuellaDep,
    puertos: ComerciosPuertosDep,
    settings: SettingsDep,
    _: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.CAJERO_GESTIONAR))],
) -> Mensaje:
    if not huella:
        raise NotFoundError("Falta la huella del dispositivo (X-Device-Huella).")
    gestion = GestionCajero(
        puertos,
        max_intentos=settings.cajero_pin_max_intentos,
        bloqueo_seg=settings.cajero_pin_bloqueo_seg,
    )
    await gestion.establecer_pin(id_usuario=id_usuario, pin=body.pin, huella=huella)
    return Mensaje(mensaje="PIN establecido para el cajero en este dispositivo.")


@router.post("/turnos/abrir", response_model=TurnoOut)
async def abrir_turno(
    body: AbrirTurnoIn,
    puertos: ComerciosPuertosDep,
    settings: SettingsDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.TURNO_OPERAR))],
) -> TurnoOut:
    gestion = GestionCajero(puertos)
    id_turno = await gestion.abrir_turno(
        id_usuario=str(actor.usuario.id), id_sucursal=body.id_sucursal
    )
    return TurnoOut(id=id_turno)


@router.post("/turnos/cerrar", response_model=CierreTurnoOut)
async def cerrar_turno(
    puertos: ComerciosPuertosDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(Permiso.TURNO_OPERAR))],
) -> CierreTurnoOut:
    resultado = await GestionCajero(puertos).cerrar_turno(id_usuario=str(actor.usuario.id))
    return CierreTurnoOut(id=resultado.id, resumen=resultado.resumen)
