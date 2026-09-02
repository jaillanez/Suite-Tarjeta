"""Infraestructura de base de datos: motor asincrónico, sesiones y base declarativa.

Única capa que conoce SQLAlchemy. La app usa el rol `tarjeta_app` (sin DDL); Alembic
usa `tarjeta_migrator` por separado (ver `migrations/env.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from tarjeta.config import Settings, get_settings
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos ORM del proyecto."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def create_engine_from_settings(settings: Settings | None = None) -> AsyncEngine:
    cfg = settings or get_settings()
    return create_async_engine(
        str(cfg.database_url),
        pool_size=cfg.database_pool_size,
        pool_pre_ping=True,
        future=True,
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine_from_settings()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provee una sesión por request (para inyección en FastAPI)."""
    async with get_sessionmaker()() as session:
        yield session


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Implementación de la unidad de trabajo sobre una sesión async de SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
