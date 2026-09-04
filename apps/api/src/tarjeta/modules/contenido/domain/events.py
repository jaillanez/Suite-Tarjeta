"""Eventos de dominio del módulo contenido."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PiezaGenerada(DomainEvent):
    id_pieza: str
    id_comercio: str
    origen: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PiezaEnviadaAModeracion(DomainEvent):
    id_pieza: str
    id_comercio: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PiezaAprobada(DomainEvent):
    id_pieza: str
    id_comercio: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PiezaRechazada(DomainEvent):
    id_pieza: str
    id_comercio: str
    motivo: str
