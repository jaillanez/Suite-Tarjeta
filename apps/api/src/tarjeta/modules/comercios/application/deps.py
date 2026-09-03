"""Contenedor de puertos de comercios."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.comercios.domain.ports import (
    ComercioRepository,
    FirmadorEstablecimiento,
    HashPin,
    InvitacionRepository,
    Outbox,
    SucursalRepository,
    TurnoRepository,
    UsuarioComercioRepository,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class ComerciosPuertos:
    # El VerificadorComerciante NO está acá: depende de padron y lo inyecta el composition
    # root en SolicitarAdhesion, para que comercios no importe otro módulo.
    uow: AbstractUnitOfWork
    comercios: ComercioRepository
    sucursales: SucursalRepository
    usuarios: UsuarioComercioRepository
    invitaciones: InvitacionRepository
    turnos: TurnoRepository
    hasher_pin: HashPin
    firmador: FirmadorEstablecimiento
    outbox: Outbox
