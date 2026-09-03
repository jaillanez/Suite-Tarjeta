"""Contenedor de puertos de padron."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.padron.domain.ports import ClientePadron, EstadoPadronRepository, Outbox
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class PadronPuertos:
    uow: AbstractUnitOfWork
    repo: EstadoPadronRepository
    cliente: ClientePadron
    outbox: Outbox
