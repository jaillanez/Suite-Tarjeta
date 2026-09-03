"""Dependencia de sesión compartida: decodifica el access token y valida la huella.

Vive en el shared kernel para que cualquier módulo la use sin importar a `identidad`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header

from tarjeta.shared.api.dependencies import SettingsDep
from tarjeta.shared.domain.errors import AuthenticationError

_MFA_SCOPE = "mfa_challenge"


@dataclass(frozen=True, slots=True)
class SesionActual:
    id_persona: str
    perfil: str
    permisos: list[str]
    huella: str | None


def get_huella(
    x_device_huella: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_device_huella


HuellaDep = Annotated[str | None, Depends(get_huella)]


def get_sesion(
    settings: SettingsDep,
    huella: HuellaDep,
    authorization: Annotated[str | None, Header()] = None,
) -> SesionActual:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Falta el token de acceso.")
    token = authorization.split(" ", 1)[1]
    try:
        data = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token inválido o expirado.") from exc

    perfil = str(data.get("perfil", ""))
    if perfil == _MFA_SCOPE:
        raise AuthenticationError("Token de acceso inválido.")

    huella_token = data.get("huella")
    huella_token = str(huella_token) if huella_token else None
    if huella_token is not None and huella_token != huella:
        raise AuthenticationError("La sesión no corresponde a este dispositivo.")

    return SesionActual(
        id_persona=str(data["sub"]),
        perfil=perfil,
        permisos=list(data.get("permisos", [])),
        huella=huella_token,
    )


SesionDep = Annotated[SesionActual, Depends(get_sesion)]
