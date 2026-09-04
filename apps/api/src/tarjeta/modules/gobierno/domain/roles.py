"""Roles municipales y matriz de permisos (§2.2), declarada como datos."""

from __future__ import annotations

from enum import StrEnum


class RolMunicipal(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMINISTRADOR = "ADMINISTRADOR"
    ENCARGADO = "ENCARGADO"
    PERSONAL = "PERSONAL"
    AUDITOR = "AUDITOR"


# Jerarquía: mayor número = más autoridad (para "rol igual o superior").
RANGO: dict[RolMunicipal, int] = {
    RolMunicipal.AUDITOR: 0,
    RolMunicipal.PERSONAL: 1,
    RolMunicipal.ENCARGADO: 2,
    RolMunicipal.ADMINISTRADOR: 3,
    RolMunicipal.SUPER_ADMIN: 4,
}


class Permiso(StrEnum):
    PARAMETRIA_EDITAR = "parametria:editar"
    REGLAS_NIVEL_EDITAR = "reglas_nivel:editar"  # 🔒 doble conformidad
    ROLES_GESTIONAR = "roles:gestionar"
    CIUDADANO_ALTA = "ciudadano:alta"
    CIUDADANO_SUSPENDER = "ciudadano:suspender"
    CIUDADANO_FICHA = "ciudadano:ficha360"
    EXCEPCION_NIVEL = "ciudadano:excepcion"
    RECLAMO_CUENTA = "ciudadano:reclamo"  # 🔒 doble conformidad
    AJUSTE_PUNTOS = "puntos:ajuste"
    EXPORTAR_MASIVO = "datos:exportar_masivo"  # 🔒 doble conformidad
    AUDITORIA_VER = "auditoria:ver"
    TABLERO_VER = "tablero:ver"
    APROBAR_DOBLE_CONF = "doble_conformidad:aprobar"
    COMERCIO_GESTIONAR = "comercio:gestionar"  # bandeja municipal de comercios (§5.1)
    PROMOCION_MODERAR = "promocion:moderar"  # cola de moderación de promociones (§07.5)


# Acciones que exigen doble conformidad (§2.2, 🔒).
DOBLE_CONFORMIDAD: frozenset[Permiso] = frozenset(
    {Permiso.REGLAS_NIVEL_EDITAR, Permiso.RECLAMO_CUENTA, Permiso.EXPORTAR_MASIVO}
)

_TODOS = set(Permiso)

MATRIZ: dict[RolMunicipal, set[Permiso]] = {
    RolMunicipal.SUPER_ADMIN: set(_TODOS),
    RolMunicipal.ADMINISTRADOR: {
        Permiso.PARAMETRIA_EDITAR,
        Permiso.REGLAS_NIVEL_EDITAR,
        Permiso.ROLES_GESTIONAR,
        Permiso.CIUDADANO_ALTA,
        Permiso.CIUDADANO_SUSPENDER,
        Permiso.CIUDADANO_FICHA,
        Permiso.EXCEPCION_NIVEL,
        Permiso.RECLAMO_CUENTA,
        Permiso.AJUSTE_PUNTOS,
        Permiso.AUDITORIA_VER,
        Permiso.TABLERO_VER,
        Permiso.APROBAR_DOBLE_CONF,
        Permiso.COMERCIO_GESTIONAR,
        Permiso.PROMOCION_MODERAR,
    },
    RolMunicipal.ENCARGADO: {
        Permiso.CIUDADANO_ALTA,
        Permiso.CIUDADANO_SUSPENDER,
        Permiso.CIUDADANO_FICHA,
        Permiso.EXCEPCION_NIVEL,
        Permiso.AJUSTE_PUNTOS,
        Permiso.TABLERO_VER,
        Permiso.PROMOCION_MODERAR,
    },
    RolMunicipal.PERSONAL: {
        Permiso.CIUDADANO_ALTA,
        Permiso.CIUDADANO_FICHA,
    },
    # AUDITOR: estrictamente solo lectura, incluida la auditoría.
    RolMunicipal.AUDITOR: {
        Permiso.AUDITORIA_VER,
        Permiso.TABLERO_VER,
        Permiso.CIUDADANO_FICHA,
    },
}


def tiene_permiso(rol: RolMunicipal, permiso: Permiso) -> bool:
    return permiso in MATRIZ.get(rol, set())


def rango_suficiente(aprobador: RolMunicipal, solicitante: RolMunicipal) -> bool:
    return RANGO[aprobador] >= RANGO[solicitante]
