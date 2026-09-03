"""Dependencias FastAPI del módulo identidad."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from tarjeta.modules.identidad.application.deps import Puertos
from tarjeta.modules.identidad.infrastructure.composition import construir_puertos
from tarjeta.shared.api.auth import HuellaDep, SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import PermissionDeniedError
from tarjeta.shared.domain.types import EntityId

# Alias para los routers de identidad (la sesión vive en el shared kernel).
ClaimsDep = SesionDep

__all__ = ["ClaimsDep", "HuellaDep", "PuertosDep", "get_ip", "get_user_agent", "require_verificada"]


@lru_cache
def _redis_cached(url: str) -> Redis:
    return Redis.from_url(url)


def get_redis(settings: SettingsDep) -> Redis:
    return _redis_cached(str(settings.redis_url))


RedisDep = Annotated[Redis, Depends(get_redis)]


def get_puertos(session: SessionDep, settings: SettingsDep, redis: RedisDep) -> Puertos:
    return construir_puertos(session, settings, redis)


PuertosDep = Annotated[Puertos, Depends(get_puertos)]


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
