"""Catálogo e inventario municipal canjeable con PM (§09.5)."""

from __future__ import annotations

import secrets
from datetime import UTC, date, datetime

from tarjeta.modules.puntos.domain.catalogo import ComprobanteInventario, ItemCatalogo
from tarjeta.modules.puntos.domain.errors import ItemNoDisponible, StockAgotado
from tarjeta.modules.puntos.domain.events import InventarioCanjeado
from tarjeta.modules.puntos.domain.moneda import TipoMoneda
from tarjeta.shared.domain.types import EntityId

from .contabilidad import Contabilidad
from .deps import PuntosPuertos


class GestionInventario:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos

    async def publicar(
        self,
        *,
        titulo: str,
        descripcion: str,
        costo_pm: int,
        stock: int,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> str:
        item = ItemCatalogo.crear(
            titulo=titulo,
            descripcion=descripcion,
            costo_pm=costo_pm,
            stock=stock,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        await self.p.catalogo.agregar(item)
        await self.p.uow.commit()
        return str(item.id)

    async def listar_activos(self) -> list[ItemCatalogo]:
        return await self.p.catalogo.listar_activos(datetime.now(UTC).date())

    async def listar_todos(self) -> list[ItemCatalogo]:
        return await self.p.catalogo.listar_todos()


class CanjearInventario:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos
        self.conta = Contabilidad(puertos)

    async def ejecutar(self, *, id_persona: str, id_item: str) -> ComprobanteInventario:
        item = await self.p.catalogo.obtener(EntityId.from_str(id_item))
        hoy = datetime.now(UTC).date()
        if item is None or not item.disponible(hoy):
            raise ItemNoDisponible("El ítem no está disponible.")
        # Reserva de cupo atómica (§09.5); si otra operación se llevó el último, rollback total.
        if not await self.p.catalogo.reservar_stock(item.id):
            raise StockAgotado("Sin stock para este ítem.")
        # Consumo de PM (FIFO, exige saldo completo). Si no alcanza, rollback (incluye el stock).
        await self.conta.consumir(
            id_titular=id_persona,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
            puntos=item.costo_pm,
            concepto=f"Canje de inventario: {item.titulo}",
            exigir_completo=True,
        )
        comprobante = ComprobanteInventario(
            id=EntityId.new(),
            id_item=str(item.id),
            id_persona=id_persona,
            titulo_item=item.titulo,
            codigo=f"INV-{secrets.token_hex(4).upper()}",
            costo_pm=item.costo_pm,
            creado_en=datetime.now(UTC),
        )
        await self.p.comprobantes.agregar(comprobante)
        await self.p.outbox.escribir(
            [
                InventarioCanjeado(
                    id_persona=id_persona,
                    id_item=str(item.id),
                    codigo=comprobante.codigo,
                    costo_pm=item.costo_pm,
                )
            ]
        )
        await self.p.uow.commit()
        return comprobante

    async def comprobantes_de(self, id_persona: str) -> list[ComprobanteInventario]:
        return await self.p.comprobantes.de_persona(id_persona)
