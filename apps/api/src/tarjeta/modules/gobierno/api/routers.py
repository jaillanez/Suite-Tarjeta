"""Router del módulo gobierno (portal municipal — backend)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tarjeta.modules.gobierno.application.doble_conformidad import (
    DecidirAprobacion,
    SolicitarAprobacion,
)
from tarjeta.modules.gobierno.application.parametria import ParametriaService
from tarjeta.modules.gobierno.domain.roles import Permiso
from tarjeta.shared.domain.types import EntityId

from .deps import Actor, GobiernoPuertosDep, requiere

router = APIRouter(prefix="/api/v1/gobierno", tags=["gobierno"])


class Mensaje(BaseModel):
    mensaje: str


class CambioParametro(BaseModel):
    valor: int
    motivo: str = ""


class SolicitudIn(BaseModel):
    accion: str
    payload: dict[str, Any] = {}


class DecisionIn(BaseModel):
    motivo: str = ""


class RegistroAuditoriaOut(BaseModel):
    id: str
    timestamp: str
    accion: str
    entidad: str
    id_entidad: str
    actor: str | None
    motivo: str


class RecaudacionOut(BaseModel):
    transiciones_a_black_post_registro: int
    distribucion_por_nivel: dict[str, int]


class AgenteOut(BaseModel):
    id_persona: str
    rol: str


class SolicitudPendienteOut(BaseModel):
    id: str
    accion: str
    solicitante: str
    fecha_expiracion: str


@router.get("/parametros", response_model=dict[str, int])
async def parametros(
    puertos: GobiernoPuertosDep,
    _: Annotated[Actor, Depends(requiere(Permiso.TABLERO_VER))],
) -> dict[str, int]:
    return await ParametriaService(puertos).todos()


@router.put("/parametros/{clave}", response_model=Mensaje)
async def cambiar_parametro(
    clave: str,
    body: CambioParametro,
    puertos: GobiernoPuertosDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.PARAMETRIA_EDITAR))],
) -> Mensaje:
    await ParametriaService(puertos).cambiar(
        clave=clave,
        valor=body.valor,
        actor=actor.id_persona,
        rol=actor.rol.value,
        motivo=body.motivo,
    )
    return Mensaje(mensaje="Parámetro actualizado.")


@router.get("/auditoria", response_model=list[RegistroAuditoriaOut])
async def auditoria(
    puertos: GobiernoPuertosDep,
    _: Annotated[Actor, Depends(requiere(Permiso.AUDITORIA_VER))],
    actor: str | None = None,
    accion: str | None = None,
    entidad: str | None = None,
    limite: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    registros = await puertos.auditoria.listar(
        actor=actor, accion=accion, entidad=entidad, limite=min(limite, 200), offset=offset
    )
    return [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat(),
            "accion": r.accion,
            "entidad": r.entidad,
            "id_entidad": r.id_entidad,
            "actor": r.id_persona_actor,
            "motivo": r.motivo,
        }
        for r in registros
    ]


@router.post("/aprobaciones", response_model=dict[str, str])
async def solicitar(
    body: SolicitudIn,
    puertos: GobiernoPuertosDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.TABLERO_VER))],
) -> dict[str, str]:
    id_solicitud = await SolicitarAprobacion(puertos).ejecutar(
        accion=body.accion,
        payload=body.payload,
        id_solicitante=actor.id_persona,
        rol=actor.rol.value,
    )
    return {"id": id_solicitud}


@router.get("/aprobaciones", response_model=list[SolicitudPendienteOut])
async def bandeja(
    puertos: GobiernoPuertosDep,
    _: Annotated[Actor, Depends(requiere(Permiso.APROBAR_DOBLE_CONF))],
) -> list[dict[str, Any]]:
    pendientes = await puertos.aprobaciones.listar_pendientes()
    return [
        {
            "id": str(s.id),
            "accion": s.accion,
            "solicitante": s.id_solicitante,
            "fecha_expiracion": s.fecha_expiracion.isoformat(),
        }
        for s in pendientes
    ]


@router.post("/aprobaciones/{id_solicitud}/aprobar", response_model=Mensaje)
async def aprobar(
    id_solicitud: str,
    body: DecisionIn,
    puertos: GobiernoPuertosDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.APROBAR_DOBLE_CONF))],
) -> Mensaje:
    solicitud = await puertos.aprobaciones.obtener(EntityId.from_str(id_solicitud))
    ejecutor = None
    if solicitud is not None and solicitud.accion == "reglas_nivel:editar":

        async def ejecutor(payload: dict[str, Any]) -> None:
            await ParametriaService(puertos).cambiar(
                clave=str(payload["clave"]),
                valor=int(payload["valor"]),
                actor=actor.id_persona,
                rol=actor.rol.value,
                motivo="doble conformidad",
            )

    await DecidirAprobacion(puertos).aprobar(
        id_solicitud=id_solicitud,
        id_aprobador=actor.id_persona,
        rol_aprobador=actor.rol.value,
        motivo=body.motivo,
        ejecutor=ejecutor,
    )
    return Mensaje(mensaje="Solicitud aprobada.")


@router.post("/aprobaciones/{id_solicitud}/rechazar", response_model=Mensaje)
async def rechazar(
    id_solicitud: str,
    body: DecisionIn,
    puertos: GobiernoPuertosDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.APROBAR_DOBLE_CONF))],
) -> Mensaje:
    await DecidirAprobacion(puertos).rechazar(
        id_solicitud=id_solicitud, id_aprobador=actor.id_persona, motivo=body.motivo
    )
    return Mensaje(mensaje="Solicitud rechazada.")


@router.get("/recaudacion", response_model=RecaudacionOut)
async def recaudacion(
    puertos: GobiernoPuertosDep,
    _: Annotated[Actor, Depends(requiere(Permiso.TABLERO_VER))],
) -> dict[str, Any]:
    return {
        "transiciones_a_black_post_registro": (
            await puertos.recaudacion.transiciones_a_black_post_registro()
        ),
        "distribucion_por_nivel": await puertos.recaudacion.distribucion_por_nivel(),
    }


@router.get("/agentes", response_model=list[AgenteOut])
async def agentes(
    puertos: GobiernoPuertosDep,
    _: Annotated[Actor, Depends(requiere(Permiso.ROLES_GESTIONAR))],
) -> list[dict[str, str]]:
    return [{"id_persona": pid, "rol": rol.value} for pid, rol in await puertos.agentes.listar()]
