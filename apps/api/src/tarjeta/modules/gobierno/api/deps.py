"""Dependencias FastAPI del módulo gobierno."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from tarjeta.modules.gobierno.application.deps import GobiernoPuertos
from tarjeta.modules.gobierno.application.permisos import exigir, resolver_rol
from tarjeta.modules.gobierno.domain.errors import PermisoDenegado
from tarjeta.modules.gobierno.domain.roles import Permiso, RolMunicipal
from tarjeta.modules.gobierno.infrastructure.composition import construir_puertos_gobierno
from tarjeta.shared.api.auth import SesionActual, SesionDep
from tarjeta.shared.api.dependencies import SessionDep


def get_puertos_gobierno(session: SessionDep) -> GobiernoPuertos:
    return construir_puertos_gobierno(session)


GobiernoPuertosDep = Annotated[GobiernoPuertos, Depends(get_puertos_gobierno)]


class Actor:
    def __init__(self, id_persona: str, rol: RolMunicipal) -> None:
        self.id_persona = id_persona
        self.rol = rol


def requiere(permiso: Permiso) -> Callable[..., Awaitable[Actor]]:
    """Devuelve una dependencia que exige `permiso` al agente municipal en sesión."""

    async def dep(sesion: SesionDep, puertos: GobiernoPuertosDep) -> Actor:
        if not sesion.perfil.startswith("MUNICIPAL"):
            raise PermisoDenegado("Se requiere un perfil municipal activo.")
        rol = await resolver_rol(puertos.agentes, sesion.id_persona)
        rol = exigir(rol, permiso)
        return Actor(sesion.id_persona, rol)

    return dep


def sesion_municipal(sesion: SesionDep) -> SesionActual:
    if not sesion.perfil.startswith("MUNICIPAL"):
        raise PermisoDenegado("Se requiere un perfil municipal activo.")
    return sesion
