"""Bus de eventos de dominio.

`EventBus` es el puerto. `InMemoryEventBus` es una implementación de proceso, útil en
desarrollo y tests. La entrega confiable entre módulos usa el patrón outbox
(ver `shared/infrastructure/outbox.py`). Python puro.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    async def publish(self, events: list[DomainEvent]) -> None: ...


class InMemoryEventBus:
    """Despacha eventos a los handlers suscriptos por nombre de evento."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers.setdefault(event_name, []).append(handler)

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            for handler in self._subscribers.get(event.name, []):
                await handler(event)
