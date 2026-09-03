"""Generador de access tokens (JWT HS256)."""

from __future__ import annotations

import time

import jwt

from tarjeta.modules.identidad.domain.ports import Claims
from tarjeta.shared.domain.errors import AuthenticationError


class JwtGenerador:
    def __init__(self, *, secret: str, ttl_seg: int) -> None:
        self._secret = secret
        self._ttl = ttl_seg

    def crear(
        self, *, id_persona: str, perfil: str, permisos: list[str], huella: str | None = None
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": id_persona,
            "perfil": perfil,
            "permisos": permisos,
            "huella": huella,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def decodificar(self, token: str) -> Claims:
        try:
            data = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token inválido o expirado.") from exc
        huella = data.get("huella")
        return Claims(
            id_persona=str(data["sub"]),
            perfil=str(data["perfil"]),
            permisos=list(data.get("permisos", [])),
            huella=str(huella) if huella else None,
        )
