"""Patrón outbox para entrega confiable de eventos de dominio.

Los eventos se persisten en la misma transacción que el cambio de estado (tabla
`outbox`) y un despachador los publica después. Esto evita perder eventos si el
proceso muere entre el commit y la publicación.

En este PASO 01 se deja el puerto y el esqueleto; la tabla ORM y su migración se
agregan cuando el primer módulo emita eventos reales (no hay lógica de negocio todavía).
"""

from __future__ import annotations

from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent


class OutboxStore(Protocol):
    """Persiste eventos de dominio en la misma transacción que el cambio de estado."""

    async def stage(self, events: list[DomainEvent]) -> None: ...
