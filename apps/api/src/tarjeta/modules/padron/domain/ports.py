"""Puertos del módulo padron."""

from __future__ import annotations

from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .estado_padron import EstadoPadron


class ClientePadron(Protocol):
    """Único contacto con el endpoint municipal. Un booleano por consulta (§7.1)."""

    async def al_dia(self, dni: str) -> bool: ...
    async def es_comerciante(self, cuit: str) -> bool: ...


class EstadoPadronRepository(Protocol):
    async def obtener(self, id_persona: EntityId) -> EstadoPadron | None: ...
    async def guardar(
        self,
        estado: EstadoPadron,
        *,
        anterior: EstadoPadron | None,
        origen: str,
    ) -> None: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...
