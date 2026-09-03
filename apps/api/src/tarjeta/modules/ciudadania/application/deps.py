"""Contenedor de puertos de ciudadania."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.ciudadania.domain.ports import (
    ExcepcionRepository,
    HistorialNivelRepository,
    Outbox,
    PerfilCiudadanoRepository,
    RateLimiter,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class CiudadaniaPuertos:
    uow: AbstractUnitOfWork
    perfiles: PerfilCiudadanoRepository
    historial: HistorialNivelRepository
    excepciones: ExcepcionRepository
    outbox: Outbox
    rate_limiter: RateLimiter
    actualizar_max_por_dia: int = 3
