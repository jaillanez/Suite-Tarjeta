"""Dependencias FastAPI del módulo identidad."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, Request
from redis.asyncio import Redis

from tarjeta.modules.identidad.application.deps import Puertos
from tarjeta.modules.identidad.domain.ports import Claims
from tarjeta.modules.identidad.infrastructure.composition import construir_puertos
from tarjeta.modules.identidad.infrastructure.jwt_generador import JwtGenerador
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import AuthenticationError, PermissionDeniedError
from tarjeta.shared.domain.types import EntityId


@lru_cache
def _redis_cached(url: str) -> Redis:
    return Redis.from_url(url)


def get_redis(settings: SettingsDep) -> Redis:
    return _redis_cached(str(settings.redis_url))


RedisDep = Annotated[Redis, Depends(get_redis)]


def get_puertos(session: SessionDep, settings: SettingsDep, redis: RedisDep) -> Puertos:
    return construir_puertos(session, settings, redis)


PuertosDep = Annotated[Puertos, Depends(get_puertos)]


def get_claims(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Claims:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Falta el token de acceso.")
    token = authorization.split(" ", 1)[1]
    gen = JwtGenerador(
        secret=settings.jwt_secret.get_secret_value(),
        ttl_seg=settings.jwt_access_ttl_seconds,
    )
    claims = gen.decodificar(token)
    # El token de reto MFA no habilita endpoints normales.
    if claims.perfil == "mfa_challenge":
        raise AuthenticationError("Token de acceso inválido.")
    return claims


ClaimsDep = Annotated[Claims, Depends(get_claims)]


async def require_verificada(claims: ClaimsDep, puertos: PuertosDep) -> str:
    """Dependencia reutilizable (§3.7): navegar sí, canjear solo si está verificada."""
    persona = await puertos.personas.obtener_por_id(EntityId.from_str(claims.id_persona))
    if persona is None or not persona.puede_canjear:
        raise PermissionDeniedError("Se requiere identidad verificada.")
    return claims.id_persona


def get_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def get_user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")
