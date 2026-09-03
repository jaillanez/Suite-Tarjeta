"""Eventos del módulo padron."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class EstadoPadronActualizado(DomainEvent):
    id_persona: str
    al_dia: bool
