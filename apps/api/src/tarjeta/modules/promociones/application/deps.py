"""Contenedor de puertos de promociones."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.promociones.domain.ports import (
    FavoritoRepository,
    Outbox,
    PerfilConfianzaRepository,
    PromocionRepository,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class PromocionesPuertos:
    uow: AbstractUnitOfWork
    promociones: PromocionRepository
    confianza: PerfilConfianzaRepository
    favoritos: FavoritoRepository
    outbox: Outbox
