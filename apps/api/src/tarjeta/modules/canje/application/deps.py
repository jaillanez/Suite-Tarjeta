"""Contenedor de puertos de canje."""

from __future__ import annotations

from dataclasses import dataclass, field

from tarjeta.modules.canje.domain.ports import (
    ComprobanteSecuencia,
    NoOpPuntos,
    Outbox,
    PuntosCanje,
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
    # §09.4: lo cablea el composition root con el módulo `puntos`; por defecto desconectado.
    puntos: PuntosCanje = field(default_factory=NoOpPuntos)
