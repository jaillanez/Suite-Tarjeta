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
    base_por_cien: int = 0  # acreditación automática por 100 pesos (0 = solo reparto, §10.0.A)
    valor_punto: int = 1  # pesos que vale un punto al pagar con puntos (ordena la caja, §09.4)
    pm_al_dia: int = 50  # PM por estar al día (§09.5)
    # §10.0.B: la generación de PM está apagada hasta que haya inventario municipal real.
    generacion_pm_activa: bool = False


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
