"""Dependencias reutilizables de FastAPI (composition root del lado HTTP)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings, get_settings
from tarjeta.shared.infrastructure.database import session_scope

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(session_scope)]


@lru_cache
def _redis_cached(url: str) -> Redis:
    return Redis.from_url(url)


def get_redis(settings: SettingsDep) -> Redis:
    return _redis_cached(str(settings.redis_url))


RedisDep = Annotated[Redis, Depends(get_redis)]
