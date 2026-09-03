"""Composición del módulo ciudadania."""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.ciudadania.application.deps import CiudadaniaPuertos
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox
from tarjeta.shared.infrastructure.redis_stores import RedisRateLimiter

from .repositories import (
    SqlAlchemyExcepcionRepository,
    SqlAlchemyHistorialNivelRepository,
    SqlAlchemyPerfilCiudadanoRepository,
)


def construir_puertos_ciudadania(session: AsyncSession, redis: Redis) -> CiudadaniaPuertos:
    return CiudadaniaPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        perfiles=SqlAlchemyPerfilCiudadanoRepository(session),
        historial=SqlAlchemyHistorialNivelRepository(session),
        excepciones=SqlAlchemyExcepcionRepository(session),
        outbox=SqlAlchemyOutbox(session),
        rate_limiter=RedisRateLimiter(redis),
    )
