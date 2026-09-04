"""Puertos del módulo canje."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .transaccion import Transaccion


@dataclass(slots=True)
class ResumenTurno:
    operaciones: int = 0
    monto_bruto: int = 0
    descuento: int = 0
    por_promocion: dict[str, int] = field(default_factory=dict)


class TransaccionRepository(Protocol):
    async def agregar(self, t: Transaccion) -> None: ...
    async def guardar(self, t: Transaccion) -> None: ...
    async def obtener(self, id: EntityId) -> Transaccion | None: ...
    async def por_idempotencia(self, clave: str) -> Transaccion | None: ...
    async def pendientes_de_persona(self, id_persona: str) -> list[Transaccion]: ...
    async def pendientes_de_comercio(self, id_comercio: str) -> list[Transaccion]: ...
    async def vencidas(self, ahora: datetime) -> list[Transaccion]: ...
    async def historial_de_persona(self, id_persona: str, limite: int) -> list[Transaccion]: ...
    async def resumen_cajero(self, id_cajero: str, desde: datetime) -> ResumenTurno: ...


class ComprobanteSecuencia(Protocol):
    async def siguiente(self) -> int: ...


class ReservaPromocion(Protocol):
    """Reserva/libera cupo de una promoción (implementado por el composition root con
    `promociones`, para no romper la independencia de módulos)."""

    async def reservar(self, id_promocion: str, id_persona: str, fecha: date) -> None: ...
    async def liberar(self, id_promocion: str, id_persona: str, fecha: date) -> None: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...
