"""Eventos de dominio del módulo puntos."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PuntosAcreditados(DomainEvent):
    id_titular: str
    tipo_moneda: str
    id_comercio: str
    puntos: int
    concepto: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PuntosConsumidos(DomainEvent):
    id_titular: str
    tipo_moneda: str
    id_comercio: str
    puntos: int
    concepto: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PuntosVencidos(DomainEvent):
    id_titular: str
    tipo_moneda: str
    id_comercio: str
    puntos: int


@dataclass(frozen=True, slots=True, kw_only=True)
class InventarioCanjeado(DomainEvent):
    id_persona: str
    id_item: str
    codigo: str
    costo_pm: int
