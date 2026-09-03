"""Verificación de permisos del comercio (mismo mecanismo declarativo del PASO 05)."""

from __future__ import annotations

from tarjeta.modules.comercios.domain.errors import PermisoComercioDenegado
from tarjeta.modules.comercios.domain.roles import Permiso, RolComercio, tiene_permiso


def exigir(rol: RolComercio, permiso: Permiso) -> None:
    if not tiene_permiso(rol, permiso):
        raise PermisoComercioDenegado("No tenés permiso para esta acción en el comercio.")
