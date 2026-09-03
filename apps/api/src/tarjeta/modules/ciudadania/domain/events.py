"""Eventos del módulo ciudadania."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class NivelCambiado(DomainEvent):
    id_persona: str
    nivel_anterior: str
    nivel_nuevo: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SolicitudActualizarEstado(DomainEvent):
    """El ciudadano pidió refrescar su estado; padron la consume y reconsulta."""

    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TarjetaEmitida(DomainEvent):
    id_persona: str
    numero_tarjeta: str
