"""Eventos de dominio del módulo canje."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class OperacionCreada(DomainEvent):
    id_transaccion: str
    id_persona: str
    id_comercio: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CanjeAplicado(DomainEvent):
    id_transaccion: str
    id_persona: str
    id_comercio: str
    monto: int
    descuento: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CanjeAnulado(DomainEvent):
    id_transaccion: str
    id_persona: str
    id_comercio: str
    motivo: str
    fuera_de_ventana: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ConflictoTopeSinConexion(DomainEvent):
    # §08.5: el tope se agotó mientras el comercio estaba sin conexión; se honró al ciudadano.
    id_transaccion: str
    id_comercio: str
    id_promocion: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DisputaAbierta(DomainEvent):
    id_transaccion: str
    id_persona: str
    id_comercio: str
    motivo: str
