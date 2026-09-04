"""Eventos de dominio del módulo promociones."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PromocionCreada(DomainEvent):
    id_promocion: str
    id_comercio: str


@dataclass(frozen=True, slots=True, kw_only=True)
class EstadoPromocionCambiado(DomainEvent):
    id_promocion: str
    id_comercio: str
    estado_anterior: str
    estado_nuevo: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PromocionModerada(DomainEvent):
    id_promocion: str
    id_comercio: str
    decision: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class NivelConfianzaCambiado(DomainEvent):
    id_comercio: str
    nivel_anterior: str
    nivel_nuevo: str
