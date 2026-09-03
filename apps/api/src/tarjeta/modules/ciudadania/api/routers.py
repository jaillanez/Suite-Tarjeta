"""Router del módulo ciudadania: Mi estado, tarjeta, actualizar, excepciones."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from tarjeta.modules.ciudadania.application.casos import (
    AplicarExcepcion,
    BloquearTarjeta,
    MiEstado,
    SolicitarActualizarEstadoUC,
)
from tarjeta.modules.ciudadania.application.deps import CiudadaniaPuertos
from tarjeta.modules.ciudadania.infrastructure.composition import construir_puertos_ciudadania
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import PermissionDeniedError

router = APIRouter(prefix="/api/v1/ciudadania", tags=["ciudadania"])


@lru_cache
def _redis_cached(url: str) -> Redis:
    return Redis.from_url(url)


def get_puertos_ciudadania(session: SessionDep, settings: SettingsDep) -> CiudadaniaPuertos:
    return construir_puertos_ciudadania(session, _redis_cached(str(settings.redis_url)))


CiudadaniaPuertosDep = Annotated[CiudadaniaPuertos, Depends(get_puertos_ciudadania)]


class MiEstadoResponse(BaseModel):
    nivel: str
    numero_tarjeta: str
    estado_tarjeta: str
    tiene_tarjeta_fisica: bool


class MensajeResponse(BaseModel):
    mensaje: str


class ExcepcionRequest(BaseModel):
    id_persona: str
    motivo: str
    dias_vigencia: int = 365


@router.get("/mi-estado", response_model=MiEstadoResponse)
async def mi_estado(sesion: SesionDep, puertos: CiudadaniaPuertosDep) -> MiEstadoResponse:
    e = await MiEstado(puertos).ejecutar(id_persona=sesion.id_persona)
    return MiEstadoResponse(
        nivel=e.nivel,
        numero_tarjeta=e.numero_tarjeta,
        estado_tarjeta=e.estado_tarjeta,
        tiene_tarjeta_fisica=e.tiene_tarjeta_fisica,
    )


@router.post("/actualizar-estado", response_model=MensajeResponse)
async def actualizar_estado(sesion: SesionDep, puertos: CiudadaniaPuertosDep) -> MensajeResponse:
    await SolicitarActualizarEstadoUC(puertos).ejecutar(id_persona=sesion.id_persona)
    return MensajeResponse(mensaje="Estado en actualización.")


@router.post("/tarjeta/bloquear", response_model=MensajeResponse)
async def bloquear_tarjeta(sesion: SesionDep, puertos: CiudadaniaPuertosDep) -> MensajeResponse:
    await BloquearTarjeta(puertos).ejecutar(id_persona=sesion.id_persona)
    return MensajeResponse(mensaje="Tarjeta bloqueada.")


@router.post("/excepciones", response_model=MensajeResponse)
async def crear_excepcion(
    body: ExcepcionRequest, sesion: SesionDep, puertos: CiudadaniaPuertosDep
) -> MensajeResponse:
    # Acción de agente municipal (la UI llega en el PASO 05); authz mínima acá.
    if not sesion.perfil.startswith("MUNICIPAL"):
        raise PermissionDeniedError("Solo un agente municipal puede otorgar excepciones.")
    await AplicarExcepcion(puertos).ejecutar(
        id_persona=body.id_persona, motivo=body.motivo, dias_vigencia=body.dias_vigencia
    )
    return MensajeResponse(mensaje="Excepción aplicada.")
