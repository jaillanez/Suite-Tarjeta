"""Contenedor de puertos de canje."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.canje.domain.ports import (
    ComprobanteSecuencia,
    Outbox,
    ReservaPromocion,
    TransaccionRepository,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class CanjePuertos:
    uow: AbstractUnitOfWork
    transacciones: TransaccionRepository
    secuencia: ComprobanteSecuencia
    reserva: ReservaPromocion
    outbox: Outbox
