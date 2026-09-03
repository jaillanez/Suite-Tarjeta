"""Portal de comercios (composition root): endpoints que cruzan varios módulos.

No es un módulo de dominio; por eso puede importar comercios/identidad/padron/gobierno
(los módulos entre sí siguen sin importarse). Cubre adhesión (verificación por CUIT contra
padron), aceptación de invitaciones (perfil de comercio en identidad), login de cajero por
PIN (tokens de identidad), baja de cajero (revoca sesiones) y la bandeja municipal.
"""

from __future__ import annotations

import csv
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tarjeta.modules.comercios.api.deps import (
    ActorComercio,
    requiere_comercio,
)
from tarjeta.modules.comercios.application.adhesion import RevisarComercio, SolicitarAdhesion
from tarjeta.modules.comercios.application.cajero import GestionCajero
from tarjeta.modules.comercios.application.sucursales import GestionSucursales
from tarjeta.modules.comercios.application.usuarios import GestionUsuarios
from tarjeta.modules.comercios.domain.comercio import EstadoComercio
from tarjeta.modules.comercios.domain.ports import VerificadorComerciante
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio
from tarjeta.modules.comercios.infrastructure.composition import construir_puertos_comercios
from tarjeta.modules.gobierno.api.deps import Actor, requiere
from tarjeta.modules.gobierno.application.doble_conformidad import (
    DecidirAprobacion,
    SolicitarAprobacion,
)
from tarjeta.modules.gobierno.domain.roles import Permiso as PermisoMunicipal
from tarjeta.modules.gobierno.infrastructure.composition import construir_puertos_gobierno
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.infrastructure.composition import construir_puertos
from tarjeta.modules.identidad.infrastructure.repositories import SqlAlchemyPersonaRepository
from tarjeta.modules.padron.infrastructure.composition import construir_cliente
from tarjeta.shared.api.auth import HuellaDep, SesionDep
from tarjeta.shared.api.dependencies import RedisDep, SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher

router = APIRouter(prefix="/api/v1/portal-comercio", tags=["portal-comercio"])


class _VerificadorPadron(VerificadorComerciante):
    def __init__(self, cliente: Any) -> None:
        self._cliente = cliente

    async def es_comerciante(self, cuit: str) -> bool:
        return bool(await self._cliente.es_comerciante(cuit))


def _verificador(settings: SettingsDep) -> VerificadorComerciante:
    return _VerificadorPadron(construir_cliente(settings))


class Mensaje(BaseModel):
    mensaje: str


class SucursalAdhesionIn(BaseModel):
    nombre: str
    direccion: str = ""
    lat: float
    lon: float
    telefono: str = ""


class AdhesionIn(BaseModel):
    cuit: str
    razon_social: str
    nombre_fantasia: str = ""
    rubro: str = ""
    logo_url: str = ""
    convenio_version: str
    sucursal: SucursalAdhesionIn


class DecisionIn(BaseModel):
    motivo: str = ""


class CargaMasivaIn(BaseModel):
    contenido: str  # CSV con encabezado: cuit,razon_social,rubro
    confirmar: bool = False


class CajeroLoginIn(BaseModel):
    id_usuario: str
    pin: str


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class ComercioBandejaOut(BaseModel):
    id: str
    cuit: str
    razon_social: str
    estado: str
    creado_en: str


class SucursalFichaOut(BaseModel):
    id: str
    nombre: str
    estado: str


class UsuarioFichaOut(BaseModel):
    id_persona: str
    rol: str
    estado: str


class FichaComercioOut(BaseModel):
    id: str
    cuit: str
    razon_social: str
    nombre_fantasia: str
    rubro: str
    estado: str
    sucursales: list[SucursalFichaOut]
    usuarios: list[UsuarioFichaOut]


# ---------------------------------------------------------------- adhesión (§06.2)


@router.post("/adhesion", response_model=dict[str, str])
async def adhesion(
    body: AdhesionIn,
    sesion: SesionDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, str]:
    puertos = construir_puertos_comercios(session, settings)
    id_comercio = await SolicitarAdhesion(puertos, _verificador(settings)).ejecutar(
        cuit=body.cuit,
        razon_social=body.razon_social,
        nombre_fantasia=body.nombre_fantasia,
        rubro=body.rubro,
        logo_url=body.logo_url,
        id_responsable=sesion.id_persona,
        convenio_version=body.convenio_version,
        ip="",
    )
    # Al menos una sucursal con pin en el mapa (§06.2.3).
    await GestionSucursales(puertos).crear(
        id_comercio=id_comercio,
        nombre=body.sucursal.nombre,
        direccion=body.sucursal.direccion,
        lat=body.sucursal.lat,
        lon=body.sucursal.lon,
        telefono=body.sucursal.telefono,
        es_casa_central=True,
    )
    # El responsable es ADMIN_COMERCIO y recibe el perfil de comercio en identidad (§06.4).
    await _crear_admin(session, settings, id_comercio=id_comercio, id_persona=sesion.id_persona)
    return {"id_comercio": id_comercio}


async def _crear_admin(
    session: SessionDep, settings: SettingsDep, *, id_comercio: str, id_persona: str
) -> None:
    from tarjeta.modules.comercios.domain.roles import RolComercio
    from tarjeta.modules.comercios.domain.usuario import UsuarioComercio

    puertos = construir_puertos_comercios(session, settings)
    usuario = UsuarioComercio.crear(
        id_comercio=EntityId.from_str(id_comercio),
        id_persona=EntityId.from_str(id_persona),
        rol=RolComercio.ADMIN_COMERCIO,
    )
    await puertos.usuarios.agregar(usuario)
    await _otorgar_perfil_comercio(
        session, settings, id_persona=id_persona, id_comercio=id_comercio, rol="ADMIN_COMERCIO"
    )
    await session.commit()


async def _otorgar_perfil_comercio(
    session: SessionDep, settings: SettingsDep, *, id_persona: str, id_comercio: str, rol: str
) -> None:
    personas = SqlAlchemyPersonaRepository(
        session,
        cipher=FieldCipher(
            settings.field_encryption_key.get_secret_value(),
            settings.field_encryption_key_version,
        ),
        pepper=settings.field_pepper.get_secret_value(),
    )
    persona = await personas.obtener_por_id(EntityId.from_str(id_persona))
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    clave = f"COMERCIO:{id_comercio}"
    if not persona.tiene_perfil(clave):
        persona.agregar_perfil(
            Perfil(tipo=TipoPerfil.COMERCIO, id_comercio=EntityId.from_str(id_comercio), rol=rol)
        )
        await personas.guardar(persona)


# ---------------------------------------------------------------- invitaciones (§06.4)


@router.post("/invitaciones/{token}/aceptar", response_model=Mensaje)
async def aceptar_invitacion(
    token: str,
    sesion: SesionDep,
    session: SessionDep,
    settings: SettingsDep,
) -> Mensaje:
    puertos = construir_puertos_comercios(session, settings)
    aceptado = await GestionUsuarios(puertos).aceptar(token=token, id_persona=sesion.id_persona)
    await _otorgar_perfil_comercio(
        session,
        settings,
        id_persona=sesion.id_persona,
        id_comercio=aceptado.id_comercio,
        rol=aceptado.rol,
    )
    await session.commit()
    return Mensaje(mensaje="Invitación aceptada. Ya podés operar en el comercio.")


# ---------------------------------------------------------------- cajero (§06.5)


@router.post("/cajero/login", response_model=TokensOut)
async def cajero_login(
    body: CajeroLoginIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    huella: HuellaDep,
) -> TokensOut:
    comercios = construir_puertos_comercios(session, settings)
    gestion = GestionCajero(
        comercios,
        max_intentos=settings.cajero_pin_max_intentos,
        bloqueo_seg=settings.cajero_pin_bloqueo_seg,
    )
    cajero = await gestion.login_pin(id_usuario=body.id_usuario, pin=body.pin, huella=huella)
    # Minta la sesión de comercio con los servicios de identidad (tokens + refresh).
    id_puertos = construir_puertos(session, settings, redis)
    perfil = f"COMERCIO:{cajero.id_comercio}"
    access = id_puertos.tokens.crear(
        id_persona=cajero.id_persona, perfil=perfil, permisos=[], huella=huella
    )
    refresh = await id_puertos.refresh.emitir(EntityId.from_str(cajero.id_persona), perfil)
    await session.commit()
    return TokensOut(access_token=access, refresh_token=refresh, token_type="bearer")


@router.post("/cajeros/{id_usuario}/baja", response_model=Mensaje)
async def dar_de_baja_cajero(
    id_usuario: str,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    _: Annotated[ActorComercio, Depends(requiere_comercio(PermisoComercio.CAJERO_GESTIONAR))],
) -> Mensaje:
    comercios = construir_puertos_comercios(session, settings)
    usuario = await GestionUsuarios(comercios).dar_de_baja(id_usuario=id_usuario)
    # Revoca sus sesiones al instante (§06.5).
    id_puertos = construir_puertos(session, settings, redis)
    await id_puertos.refresh.revocar_todo_de(usuario.id_persona)
    await session.commit()
    return Mensaje(mensaje="Cajero dado de baja; sus sesiones fueron revocadas.")


# ---------------------------------------------------------------- bandeja municipal (§06.6)


@router.get("/bandeja", response_model=list[ComercioBandejaOut])
async def bandeja(
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> list[dict[str, Any]]:
    comercios = construir_puertos_comercios(session, settings)
    pendientes = await comercios.comercios.listar(
        [
            EstadoComercio.SOLICITADA,
            EstadoComercio.EN_REVISION,
            EstadoComercio.DOCUMENTACION_PENDIENTE,
        ]
    )
    return [
        {
            "id": str(c.id),
            "cuit": c.cuit,
            "razon_social": c.razon_social,
            "estado": c.estado.value,
            "creado_en": c.creado_en.isoformat(),
        }
        for c in pendientes
    ]


@router.get("/comercios/{id_comercio}/ficha", response_model=FichaComercioOut)
async def ficha_comercio(
    id_comercio: str,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> dict[str, Any]:
    comercios = construir_puertos_comercios(session, settings)
    pid = EntityId.from_str(id_comercio)
    c = await comercios.comercios.obtener(pid)
    if c is None:
        raise NotFoundError("Comercio inexistente.")
    sucursales = await comercios.sucursales.listar_por_comercio(pid)
    usuarios = await comercios.usuarios.listar_por_comercio(pid)
    # No se exponen datos personales del ciudadano: solo id_persona y rol.
    return {
        "id": str(c.id),
        "cuit": c.cuit,
        "razon_social": c.razon_social,
        "nombre_fantasia": c.nombre_fantasia,
        "rubro": c.rubro,
        "estado": c.estado.value,
        "sucursales": [
            {"id": str(s.id), "nombre": s.nombre, "estado": s.estado.value} for s in sucursales
        ],
        "usuarios": [
            {"id_persona": str(u.id_persona), "rol": u.rol.value, "estado": u.estado.value}
            for u in usuarios
        ],
    }


def _revisar(session: SessionDep, settings: SettingsDep) -> RevisarComercio:
    return RevisarComercio(construir_puertos_comercios(session, settings))


@router.post("/comercios/{id_comercio}/tomar", response_model=Mensaje)
async def tomar(
    id_comercio: str,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> Mensaje:
    await _revisar(session, settings).tomar(id_comercio)
    return Mensaje(mensaje="Comercio en revisión.")


@router.post("/comercios/{id_comercio}/aprobar", response_model=Mensaje)
async def aprobar(
    id_comercio: str,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> Mensaje:
    await _revisar(session, settings).aprobar(id_comercio)
    return Mensaje(mensaje="Comercio aprobado y activo.")


@router.post("/comercios/{id_comercio}/rechazar", response_model=Mensaje)
async def rechazar(
    id_comercio: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> Mensaje:
    await _revisar(session, settings).rechazar(id_comercio, body.motivo)
    return Mensaje(mensaje="Comercio rechazado.")


@router.post("/comercios/{id_comercio}/pedir-documentacion", response_model=Mensaje)
async def pedir_documentacion(
    id_comercio: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> Mensaje:
    await _revisar(session, settings).pedir_documentacion(id_comercio, body.motivo)
    return Mensaje(mensaje="Se pidió documentación.")


@router.post("/comercios/{id_comercio}/suspender", response_model=Mensaje)
async def suspender(
    id_comercio: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> Mensaje:
    await _revisar(session, settings).suspender(id_comercio, body.motivo)
    return Mensaje(mensaje="Comercio suspendido.")


# ------ baja definitiva con doble conformidad (§06.2) ------


@router.post("/comercios/{id_comercio}/baja-solicitar", response_model=dict[str, str])
async def baja_solicitar(
    id_comercio: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> dict[str, str]:
    gob = construir_puertos_gobierno(session)
    id_solicitud = await SolicitarAprobacion(gob).ejecutar(
        accion="comercio:baja",
        payload={"id_comercio": id_comercio, "motivo": body.motivo},
        id_solicitante=actor.id_persona,
        rol=actor.rol.value,
    )
    return {"id": id_solicitud}


@router.post("/baja/{id_solicitud}/aprobar", response_model=Mensaje)
async def baja_aprobar(
    id_solicitud: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[Actor, Depends(requiere(PermisoMunicipal.APROBAR_DOBLE_CONF))],
) -> Mensaje:
    revisar = _revisar(session, settings)

    async def ejecutor(payload: dict[str, Any]) -> None:
        await revisar.dar_de_baja(str(payload["id_comercio"]), str(payload.get("motivo", "")))

    await DecidirAprobacion(construir_puertos_gobierno(session)).aprobar(
        id_solicitud=id_solicitud,
        id_aprobador=actor.id_persona,
        rol_aprobador=actor.rol.value,
        motivo=body.motivo,
        ejecutor=ejecutor,
    )
    return Mensaje(mensaje="Baja de comercio aprobada.")


# ------ carga masiva por CSV (§06.6) ------


@router.post("/carga-masiva")
async def carga_masiva(
    body: CargaMasivaIn,
    session: SessionDep,
    settings: SettingsDep,
    sesion: SesionDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.COMERCIO_GESTIONAR))],
) -> dict[str, Any]:
    puertos = construir_puertos_comercios(session, settings)
    verificador = _verificador(settings)
    lector = csv.DictReader(io.StringIO(body.contenido))
    filas: list[dict[str, Any]] = []
    validas: list[dict[str, str]] = []
    for i, fila in enumerate(lector, start=1):
        cuit = (fila.get("cuit") or "").strip()
        razon = (fila.get("razon_social") or "").strip()
        rubro = (fila.get("rubro") or "").strip()
        error = None
        if not cuit or not razon:
            error = "Faltan cuit o razon_social."
        elif await puertos.comercios.obtener_por_cuit(cuit) is not None:
            error = "Ya existe un comercio con ese CUIT."
        elif not await verificador.es_comerciante(cuit):
            error = "El CUIT no figura como comerciante."
        filas.append({"fila": i, "cuit": cuit, "ok": error is None, "error": error})
        if error is None:
            validas.append({"cuit": cuit, "razon_social": razon, "rubro": rubro})

    creados = 0
    if body.confirmar:
        for v in validas:
            await SolicitarAdhesion(puertos, verificador).ejecutar(
                cuit=v["cuit"],
                razon_social=v["razon_social"],
                nombre_fantasia="",
                rubro=v["rubro"],
                logo_url="",
                id_responsable=sesion.id_persona,
                convenio_version="carga-masiva",
                ip="",
            )
            creados += 1

    return {"filas": filas, "validas": len(validas), "creados": creados}
