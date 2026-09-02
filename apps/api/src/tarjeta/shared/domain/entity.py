"""Entidades y raíces de agregado.

`Entity` tiene identidad y se compara por ella. `AggregateRoot` es la frontera de
consistencia: acumula eventos de dominio que la capa de aplicación publica al confirmar.
"""

from __future__ import annotations

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId


class Entity:
    """Objeto con identidad estable. La igualdad depende del id, no de los atributos."""

    def __init__(self, id: EntityId) -> None:
        self._id = id

    @property
    def id(self) -> EntityId:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))


class AggregateRoot(Entity):
    """Raíz de agregado: única puerta de entrada a su grafo y fuente de eventos."""

    def __init__(self, id: EntityId) -> None:
        super().__init__(id)
        self._events: list[DomainEvent] = []

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Devuelve y limpia los eventos acumulados (los toma la unidad de trabajo)."""
        eventos = self._events[:]
        self._events.clear()
        return eventos
