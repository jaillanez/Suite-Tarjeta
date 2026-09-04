"""Contenedor de puertos y configuración del módulo contenido."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.contenido.domain.ports import (
    AlmacenObjetos,
    Compositor,
    CreditoRepository,
    GeneradorImagen,
    Outbox,
    PiezaRepository,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(frozen=True, slots=True)
class ContenidoConfig:
    cuota_mensual: int = 10
    # §11.2: la palanca de costo. Cuántas imágenes entrega un crédito (4 -> 2 parte el costo).
    variantes_por_credito: int = 4
    tamano: str = "1024x1024"
    modelo: str = "simulacion"
    # Para el cálculo de costo mensual (no gasta nada; solo informa).
    precio_unitario_centavos: int = 0


@dataclass(slots=True)
class ContenidoPuertos:
    uow: AbstractUnitOfWork
    piezas: PiezaRepository
    creditos: CreditoRepository
    generador: GeneradorImagen
    compositor: Compositor
    almacen: AlmacenObjetos
    outbox: Outbox
    config: ContenidoConfig
