"""Enumeraciones del grupo familiar (§10)."""

from __future__ import annotations

from enum import StrEnum


class ModoBilletera(StrEnum):
    COMUN = "COMUN"  # los canjes van al pozo del grupo; cualquiera gasta de ahí (§10.5)
    INDIVIDUAL = "INDIVIDUAL"  # cada uno acumula y gasta lo suyo; el grupo solo hereda nivel


class EstadoGrupo(StrEnum):
    ACTIVO = "ACTIVO"
    DISUELTO = "DISUELTO"


class RolGrupo(StrEnum):
    TITULAR = "TITULAR"
    MIEMBRO = "MIEMBRO"


class EstadoMiembro(StrEnum):
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"  # el titular lo frenó temporalmente (§10.6)
    BAJA = "BAJA"


class EstadoInvitacion(StrEnum):
    PENDIENTE = "PENDIENTE"
    ACEPTADA = "ACEPTADA"
    VENCIDA = "VENCIDA"
    CANCELADA = "CANCELADA"
