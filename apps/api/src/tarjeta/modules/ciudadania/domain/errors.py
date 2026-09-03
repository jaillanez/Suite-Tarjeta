"""Errores del módulo ciudadania."""

from __future__ import annotations

from tarjeta.shared.domain.errors import NotFoundError


class PerfilCiudadanoInexistente(NotFoundError):
    code = "perfil_ciudadano_inexistente"
