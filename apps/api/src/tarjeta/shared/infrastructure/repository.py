"""Repositorio genérico sobre SQLAlchemy.

Los repositorios concretos de cada módulo heredan de acá e implementan los puertos
definidos en su `domain`. La capa de aplicación depende del puerto, no de esta clase.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.shared.infrastructure.database import Base


class SQLAlchemyRepository[TModel: Base]:
    """Operaciones CRUD básicas sobre un modelo ORM."""

    model: type[TModel]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, entity: TModel) -> None:
        self.session.add(entity)

    async def get(self, id_: Any) -> TModel | None:
        return await self.session.get(self.model, id_)

    async def list(self) -> Sequence[TModel]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()
