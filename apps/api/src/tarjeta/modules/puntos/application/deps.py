"""Contenedor de puertos y configuración del módulo puntos."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.puntos.domain.ports import (
    BilleteraRepository,
    ComprobanteInventarioRepository,
    ItemCatalogoRepository,
    LoteRepository,
    MovimientoRepository,
    Outbox,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(frozen=True, slots=True)
class PuntosConfig:
    vencimiento_meses: int = 24
    base_por_cien: int = 1  # puntos base por cada 100 pesos (antes del multiplicador)
    valor_punto: int = 1  # pesos que vale un punto al pagar con puntos (ordena la caja, §09.4)
    pm_al_dia: int = 50  # PM por estar al día (§09.5, regla activa)


@dataclass(slots=True)
class PuntosPuertos:
    uow: AbstractUnitOfWork
    billeteras: BilleteraRepository
    lotes: LoteRepository
    movimientos: MovimientoRepository
    catalogo: ItemCatalogoRepository
    comprobantes: ComprobanteInventarioRepository
    outbox: Outbox
    config: PuntosConfig
