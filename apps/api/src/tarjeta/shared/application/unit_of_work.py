"""Puerto de unidad de trabajo (asincrónica).

Define la interfaz que la capa de aplicación usa para delimitar una transacción.
La implementación concreta sobre SQLAlchemy vive en `shared/infrastructure/database.py`
(única capa que conoce SQLAlchemy). Este módulo no importa infraestructura.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class AbstractUnitOfWork(ABC):
    """Delimita una transacción. El commit es explícito; al salir con error, rollback."""

    async def __aenter__(self) -> AbstractUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
