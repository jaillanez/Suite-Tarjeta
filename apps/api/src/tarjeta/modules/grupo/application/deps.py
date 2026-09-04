"""Contenedor de puertos del módulo grupo."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.grupo.domain.ports import (
    AlertaRepository,
    AvisoRepository,
    GrupoRepository,
    InvitacionRepository,
    Outbox,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class GrupoPuertos:
    uow: AbstractUnitOfWork
    grupos: GrupoRepository
    invitaciones: InvitacionRepository
    alertas: AlertaRepository
    avisos: AvisoRepository
    outbox: Outbox
