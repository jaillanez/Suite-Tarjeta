"""Inventario municipal canjeable con PM (§09.5).

Sin inventario los PM no sirven para nada y el vecino los ve como un número decorativo. Un ítem
tiene stock, vigencia y costo en PM. El canje reserva el cupo con la misma disciplina atómica de
los topes y emite un comprobante con código para presentar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tarjeta.shared.domain.types import EntityId


class EstadoItem(StrEnum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


@dataclass(slots=True)
class ItemCatalogo:
    id: EntityId
    titulo: str
    descripcion: str
    costo_pm: int
    stock: int
    fecha_desde: date
    fecha_hasta: date
    estado: EstadoItem
    creado_en: datetime

    @classmethod
    def crear(
        cls,
        *,
        titulo: str,
        descripcion: str,
        costo_pm: int,
        stock: int,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> ItemCatalogo:
        if costo_pm <= 0:
            raise ValueError("El costo en PM debe ser positivo.")
        if stock < 0:
            raise ValueError("El stock no puede ser negativo.")
        return cls(
            id=EntityId.new(),
            titulo=titulo,
            descripcion=descripcion,
            costo_pm=costo_pm,
            stock=stock,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=EstadoItem.ACTIVO,
            creado_en=datetime.now().astimezone(),
        )

    def disponible(self, hoy: date) -> bool:
        return (
            self.estado is EstadoItem.ACTIVO
            and self.stock > 0
            and self.fecha_desde <= hoy <= self.fecha_hasta
        )


@dataclass(slots=True)
class ComprobanteInventario:
    id: EntityId
    id_item: str
    id_persona: str
    titulo_item: str
    codigo: str
    costo_pm: int
    creado_en: datetime
