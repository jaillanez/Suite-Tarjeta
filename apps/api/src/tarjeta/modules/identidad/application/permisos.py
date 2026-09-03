"""Permisos por perfil (placeholder; el detalle fino llega con cada módulo)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil

_PERMISOS: dict[TipoPerfil, list[str]] = {
    TipoPerfil.CIUDADANO: ["ciudadano:ver", "ciudadano:canjear"],
    TipoPerfil.COMERCIO: ["comercio:caja", "comercio:ver"],
    TipoPerfil.MUNICIPAL: ["municipal:operar"],
}


def permisos_de(perfil: Perfil) -> list[str]:
    return list(_PERMISOS.get(perfil.tipo, []))
