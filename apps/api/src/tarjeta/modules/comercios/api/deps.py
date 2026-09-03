"""Dependencias FastAPI del módulo comercios."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from tarjeta.modules.comercios.application.deps import ComerciosPuertos
from tarjeta.modules.comercios.application.permisos import exigir
from tarjeta.modules.comercios.domain.errors import PermisoComercioDenegado
from tarjeta.modules.comercios.domain.roles import Permiso
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio
from tarjeta.modules.comercios.infrastructure.composition import construir_puertos_comercios
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.types import EntityId

_PREFIJO = "COMERCIO:"


def get_puertos_comercios(session: SessionDep, settings: SettingsDep) -> ComerciosPuertos:
    return construir_puertos_comercios(session, settings)


ComerciosPuertosDep = Annotated[ComerciosPuertos, Depends(get_puertos_comercios)]


class ActorComercio:
    def __init__(self, usuario: UsuarioComercio) -> None:
        self.usuario = usuario
        self.id_persona = str(usuario.id_persona)
        self.id_comercio = usuario.id_comercio
        self.rol = usuario.rol


async def actor_comercio(sesion: SesionDep, puertos: ComerciosPuertosDep) -> ActorComercio:
    if not sesion.perfil.startswith(_PREFIJO):
        raise PermisoComercioDenegado("Se requiere un perfil de comercio activo.")
    id_comercio = EntityId.from_str(sesion.perfil[len(_PREFIJO) :])
    usuario = await puertos.usuarios.obtener_por_persona_y_comercio(
        EntityId.from_str(sesion.id_persona), id_comercio
    )
    if usuario is None or not usuario.activo:
        raise PermisoComercioDenegado("No sos usuario activo de este comercio.")
    return ActorComercio(usuario)


ActorComercioDep = Annotated[ActorComercio, Depends(actor_comercio)]


def requiere_comercio(permiso: Permiso) -> Callable[..., Awaitable[ActorComercio]]:
    async def dep(actor: ActorComercioDep) -> ActorComercio:
        exigir(actor.rol, permiso)
        return actor

    return dep
