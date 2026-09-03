"""Contenedor de puertos de gobierno."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.gobierno.domain.ports import (
    AgenteRepository,
    AprobacionRepository,
    AuditoriaRepository,
    ParametroRepository,
    RecaudacionRepository,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class GobiernoPuertos:
    uow: AbstractUnitOfWork
    auditoria: AuditoriaRepository
    aprobaciones: AprobacionRepository
    parametros: ParametroRepository
    agentes: AgenteRepository
    recaudacion: RecaudacionRepository
