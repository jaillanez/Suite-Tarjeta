"""Roles del comercio y matriz de permisos (§2.1), declarada como datos.

Mismo mecanismo que la matriz municipal del PASO 05 (gobierno), aplicado al comercio.
"""

from __future__ import annotations

from enum import StrEnum


class RolComercio(StrEnum):
    ADMIN_COMERCIO = "ADMIN_COMERCIO"
    ADMIN_SUCURSALES = "ADMIN_SUCURSALES"
    ENCARGADO = "ENCARGADO"
    CAJERO = "CAJERO"


# Roles cuyo alcance se limita a las sucursales asignadas (§2.1).
ALCANCE_POR_SUCURSAL: frozenset[RolComercio] = frozenset(
    {RolComercio.ADMIN_SUCURSALES, RolComercio.ENCARGADO, RolComercio.CAJERO}
)

# Roles que requieren MFA para operar (§06.4, regla del PASO 05 aplicada por rol).
REQUIERE_MFA: frozenset[RolComercio] = frozenset({RolComercio.ADMIN_COMERCIO})


class Permiso(StrEnum):
    COMERCIO_EDITAR = "comercio:editar"
    SUCURSAL_GESTIONAR = "sucursal:gestionar"
    USUARIO_GESTIONAR = "usuario:gestionar"
    CAJERO_GESTIONAR = "cajero:gestionar"
    TURNO_OPERAR = "turno:operar"
    CANJE_OPERAR = "canje:operar"  # habilita la caja (paso siguiente)
    REPORTES_VER = "reportes:ver"
    PROMOCION_GESTIONAR = "promocion:gestionar"  # cargar/editar/pausar promociones (§07.8)


MATRIZ: dict[RolComercio, set[Permiso]] = {
    RolComercio.ADMIN_COMERCIO: set(Permiso),
    RolComercio.ADMIN_SUCURSALES: {
        Permiso.SUCURSAL_GESTIONAR,
        Permiso.USUARIO_GESTIONAR,
        Permiso.CAJERO_GESTIONAR,
        Permiso.TURNO_OPERAR,
        Permiso.REPORTES_VER,
        Permiso.PROMOCION_GESTIONAR,
    },
    RolComercio.ENCARGADO: {
        Permiso.CAJERO_GESTIONAR,
        Permiso.TURNO_OPERAR,
        Permiso.REPORTES_VER,
        Permiso.PROMOCION_GESTIONAR,
    },
    # El cajero solo opera la caja y su turno.
    RolComercio.CAJERO: {
        Permiso.TURNO_OPERAR,
        Permiso.CANJE_OPERAR,
    },
}


def tiene_permiso(rol: RolComercio, permiso: Permiso) -> bool:
    return permiso in MATRIZ.get(rol, set())


def alcance_limitado(rol: RolComercio) -> bool:
    return rol in ALCANCE_POR_SUCURSAL
