"""Resolución y verificación de permisos municipales."""

from __future__ import annotations

from tarjeta.modules.gobierno.domain.errors import PermisoDenegado
from tarjeta.modules.gobierno.domain.ports import AgenteRepository
from tarjeta.modules.gobierno.domain.roles import Permiso, RolMunicipal, tiene_permiso
from tarjeta.shared.domain.types import EntityId


async def resolver_rol(agentes: AgenteRepository, id_persona: str) -> RolMunicipal | None:
    return await agentes.rol_de(EntityId.from_str(id_persona))


def exigir(rol: RolMunicipal | None, permiso: Permiso) -> RolMunicipal:
    if rol is None or not tiene_permiso(rol, permiso):
        raise PermisoDenegado("No tenés permiso para esta acción.")
    return rol
