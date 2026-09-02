"""Contratos de casos de uso: comandos, consultas y sus handlers.

Los handlers concretos viven en cada módulo (`modules/<x>/application`). Acá solo
están las formas genéricas. Python puro.
"""

from __future__ import annotations

from typing import Protocol, TypeVar


class Command:
    """Intención de cambiar el estado del sistema."""


class Query:
    """Intención de leer estado sin modificarlo."""


TCommand = TypeVar("TCommand", bound=Command, contravariant=True)
TQuery = TypeVar("TQuery", bound=Query, contravariant=True)
TResult = TypeVar("TResult", covariant=True)


class CommandHandler(Protocol[TCommand, TResult]):
    async def handle(self, command: TCommand) -> TResult: ...


class QueryHandler(Protocol[TQuery, TResult]):
    async def handle(self, query: TQuery) -> TResult: ...
