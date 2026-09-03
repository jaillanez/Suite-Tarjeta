"""Router del módulo padron: estado propio del ciudadano en sesión."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tarjeta.modules.padron.application.deps import PadronPuertos
from tarjeta.modules.padron.infrastructure.composition import construir_puertos_padron
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1/padron", tags=["padron"])


def get_puertos_padron(session: SessionDep, settings: SettingsDep) -> PadronPuertos:
    return construir_puertos_padron(session, settings)


PadronPuertosDep = Annotated[PadronPuertos, Depends(get_puertos_padron)]


class MiEstadoPadronResponse(BaseModel):
    consultado: bool
    al_dia: bool | None = None
    fecha_ultima_consulta: str | None = None
    horas_desde_consulta: int | None = None


@router.get("/mi-estado", response_model=MiEstadoPadronResponse)
async def mi_estado(sesion: SesionDep, puertos: PadronPuertosDep) -> MiEstadoPadronResponse:
    estado = await puertos.repo.obtener(EntityId.from_str(sesion.id_persona))
    if estado is None:
        return MiEstadoPadronResponse(consultado=False)
    horas = int((datetime.now(UTC) - estado.fecha_ultima_consulta).total_seconds() // 3600)
    return MiEstadoPadronResponse(
        consultado=True,
        al_dia=estado.al_dia,
        fecha_ultima_consulta=estado.fecha_ultima_consulta.isoformat(),
        horas_desde_consulta=horas,
    )
