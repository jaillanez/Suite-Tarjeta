"""Repositorios del módulo puntos (libro append-only, lotes FIFO, inventario)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.puntos.domain.billetera import Billetera
from tarjeta.modules.puntos.domain.catalogo import (
    ComprobanteInventario,
    EstadoItem,
    ItemCatalogo,
)
from tarjeta.modules.puntos.domain.lote import LotePuntos
from tarjeta.modules.puntos.domain.moneda import (
    COMERCIO_MUNICIPAL,
    OrigenPuntos,
    TipoMoneda,
    TipoTitular,
)
from tarjeta.modules.puntos.domain.movimiento import MovimientoBilletera, TipoMovimiento
from tarjeta.shared.domain.types import EntityId

from .models import (
    BilleteraModel,
    ComprobanteInventarioModel,
    ItemCatalogoModel,
    LotePuntosModel,
    MovimientoBilleteraModel,
)


def _comercio(tipo_moneda: TipoMoneda, id_comercio: str | None) -> str:
    return COMERCIO_MUNICIPAL if tipo_moneda is TipoMoneda.PM else (id_comercio or "")


def _billetera_to_domain(m: BilleteraModel) -> Billetera:
    return Billetera(
        id=EntityId(m.id),
        tipo_titular=TipoTitular(m.tipo_titular),
        id_titular=m.id_titular,
        tipo_moneda=TipoMoneda(m.tipo_moneda),
        id_comercio=m.id_comercio,
        saldo=m.saldo,
        creada_en=m.creada_en,
    )


class SqlAlchemyBilleteraRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def obtener_o_crear(
        self,
        *,
        tipo_titular: TipoTitular,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
    ) -> Billetera:
        comercio = _comercio(tipo_moneda, id_comercio)
        # INSERT idempotente + SELECT FOR UPDATE: crea si falta y bloquea la fila (§09.2).
        await self._s.execute(
            text(
                "INSERT INTO billetera "
                "(id, tipo_titular, id_titular, tipo_moneda, id_comercio, saldo, creada_en) "
                "VALUES (:id, :tt, :it, :tm, :ic, 0, :ce) "
                "ON CONFLICT (tipo_titular, id_titular, tipo_moneda, id_comercio) DO NOTHING"
            ),
            {
                "id": EntityId.new().value,
                "tt": tipo_titular.value,
                "it": id_titular,
                "tm": tipo_moneda.value,
                "ic": comercio,
                "ce": datetime.now(UTC),
            },
        )
        m = (
            await self._s.execute(
                select(BilleteraModel)
                .where(
                    BilleteraModel.tipo_titular == tipo_titular.value,
                    BilleteraModel.id_titular == id_titular,
                    BilleteraModel.tipo_moneda == tipo_moneda.value,
                    BilleteraModel.id_comercio == comercio,
                )
                .with_for_update()
            )
        ).scalar_one()
        return _billetera_to_domain(m)

    async def obtener(
        self,
        *,
        tipo_titular: TipoTitular,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
    ) -> Billetera | None:
        comercio = _comercio(tipo_moneda, id_comercio)
        m = (
            await self._s.execute(
                select(BilleteraModel).where(
                    BilleteraModel.tipo_titular == tipo_titular.value,
                    BilleteraModel.id_titular == id_titular,
                    BilleteraModel.tipo_moneda == tipo_moneda.value,
                    BilleteraModel.id_comercio == comercio,
                )
            )
        ).scalar_one_or_none()
        return _billetera_to_domain(m) if m else None

    async def ajustar_saldo(self, id_billetera: EntityId, delta: int) -> int:
        nuevo = (
            await self._s.execute(
                text("UPDATE billetera SET saldo = saldo + :d WHERE id = :id RETURNING saldo"),
                {"d": delta, "id": id_billetera.value},
            )
        ).scalar_one()
        return int(nuevo)

    async def bloquear(self, id_billetera: EntityId) -> Billetera | None:
        m = (
            await self._s.execute(
                select(BilleteraModel)
                .where(BilleteraModel.id == id_billetera.value)
                .with_for_update()
            )
        ).scalar_one_or_none()
        return _billetera_to_domain(m) if m else None

    async def pc_de_titular(self, id_titular: str) -> list[Billetera]:
        rows = (
            await self._s.execute(
                select(BilleteraModel)
                .where(
                    BilleteraModel.id_titular == id_titular,
                    BilleteraModel.tipo_moneda == TipoMoneda.PC.value,
                )
                .order_by(BilleteraModel.id_comercio)
            )
        ).scalars()
        return [_billetera_to_domain(m) for m in rows]

    async def por_id(self, id_billetera: EntityId) -> Billetera | None:
        m = await self._s.get(BilleteraModel, id_billetera.value)
        return _billetera_to_domain(m) if m else None


def _lote_to_domain(m: LotePuntosModel) -> LotePuntos:
    return LotePuntos(
        id=EntityId(m.id),
        id_billetera=EntityId(m.id_billetera),
        monto_original=m.monto_original,
        saldo_restante=m.saldo_restante,
        vence_en=m.vence_en,
        origen_puntos=OrigenPuntos(m.origen_puntos),
        creado_en=m.creado_en,
        id_transaccion_canje=m.id_transaccion_canje,
        vencido=m.vencido,
    )


class SqlAlchemyLoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, lote: LotePuntos) -> None:
        self._s.add(
            LotePuntosModel(
                id=lote.id.value,
                id_billetera=lote.id_billetera.value,
                monto_original=lote.monto_original,
                saldo_restante=lote.saldo_restante,
                vence_en=lote.vence_en,
                origen_puntos=lote.origen_puntos.value,
                creado_en=lote.creado_en,
                id_transaccion_canje=lote.id_transaccion_canje,
                vencido=lote.vencido,
            )
        )
        await self._s.flush()

    async def obtener(self, id_lote: EntityId) -> LotePuntos | None:
        m = await self._s.get(LotePuntosModel, id_lote.value)
        return _lote_to_domain(m) if m else None

    async def disponibles_fifo(self, id_billetera: EntityId, hoy: date) -> list[LotePuntos]:
        rows = (
            await self._s.execute(
                select(LotePuntosModel)
                .where(
                    LotePuntosModel.id_billetera == id_billetera.value,
                    LotePuntosModel.vencido.is_(False),
                    LotePuntosModel.saldo_restante > 0,
                    LotePuntosModel.vence_en >= hoy,
                )
                .order_by(LotePuntosModel.vence_en.asc(), LotePuntosModel.creado_en.asc())
            )
        ).scalars()
        return [_lote_to_domain(m) for m in rows]

    async def descontar(self, id_lote: EntityId, cantidad: int) -> None:
        await self._s.execute(
            text("UPDATE lote_puntos SET saldo_restante = saldo_restante - :c WHERE id = :id"),
            {"c": cantidad, "id": id_lote.value},
        )

    async def por_vencer(
        self, id_billetera: EntityId, desde: date, hasta: date
    ) -> list[LotePuntos]:
        rows = (
            await self._s.execute(
                select(LotePuntosModel)
                .where(
                    LotePuntosModel.id_billetera == id_billetera.value,
                    LotePuntosModel.vencido.is_(False),
                    LotePuntosModel.saldo_restante > 0,
                    LotePuntosModel.vence_en >= desde,
                    LotePuntosModel.vence_en <= hasta,
                )
                .order_by(LotePuntosModel.vence_en.asc())
            )
        ).scalars()
        return [_lote_to_domain(m) for m in rows]

    async def vencidos_pendientes(self, hoy: date, limite: int) -> list[LotePuntos]:
        rows = (
            await self._s.execute(
                select(LotePuntosModel)
                .where(
                    LotePuntosModel.vencido.is_(False),
                    LotePuntosModel.saldo_restante > 0,
                    LotePuntosModel.vence_en < hoy,
                )
                .order_by(LotePuntosModel.vence_en.asc())
                .limit(limite)
            )
        ).scalars()
        return [_lote_to_domain(m) for m in rows]

    async def marcar_vencido(self, id_lote: EntityId) -> None:
        await self._s.execute(
            text("UPDATE lote_puntos SET vencido = TRUE, saldo_restante = 0 WHERE id = :id"),
            {"id": id_lote.value},
        )


def _mov_to_domain(m: MovimientoBilleteraModel) -> MovimientoBilletera:
    return MovimientoBilletera(
        id=EntityId(m.id),
        id_billetera=EntityId(m.id_billetera),
        tipo=TipoMovimiento(m.tipo),
        monto=m.monto,
        origen_puntos=OrigenPuntos(m.origen_puntos),
        creado_en=m.creado_en,
        id_lote=EntityId(m.id_lote) if m.id_lote else None,
        id_transaccion_canje=m.id_transaccion_canje,
        id_movimiento_original=EntityId(m.id_movimiento_original)
        if m.id_movimiento_original
        else None,
        clave_dedup=m.clave_dedup,
        concepto=m.concepto,
    )


class SqlAlchemyMovimientoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, movimiento: MovimientoBilletera) -> None:
        self._s.add(
            MovimientoBilleteraModel(
                id=movimiento.id.value,
                id_billetera=movimiento.id_billetera.value,
                tipo=movimiento.tipo.value,
                monto=movimiento.monto,
                origen_puntos=movimiento.origen_puntos.value,
                creado_en=movimiento.creado_en,
                id_lote=movimiento.id_lote.value if movimiento.id_lote else None,
                id_transaccion_canje=movimiento.id_transaccion_canje,
                id_movimiento_original=(
                    movimiento.id_movimiento_original.value
                    if movimiento.id_movimiento_original
                    else None
                ),
                clave_dedup=movimiento.clave_dedup,
                concepto=movimiento.concepto,
            )
        )
        await self._s.flush()

    async def existe(self, clave_dedup: str) -> bool:
        row = await self._s.scalar(
            select(MovimientoBilleteraModel.id).where(
                MovimientoBilleteraModel.clave_dedup == clave_dedup
            )
        )
        return row is not None

    async def suma(self, id_billetera: EntityId) -> int:
        total = await self._s.scalar(
            select(func.coalesce(func.sum(MovimientoBilleteraModel.monto), 0)).where(
                MovimientoBilleteraModel.id_billetera == id_billetera.value
            )
        )
        return int(total or 0)

    async def listar(self, id_billetera: EntityId, limite: int) -> list[MovimientoBilletera]:
        rows = (
            await self._s.execute(
                select(MovimientoBilleteraModel)
                .where(MovimientoBilleteraModel.id_billetera == id_billetera.value)
                .order_by(MovimientoBilleteraModel.creado_en.desc())
                .limit(limite)
            )
        ).scalars()
        return [_mov_to_domain(m) for m in rows]

    async def por_transaccion(self, id_transaccion: str) -> list[MovimientoBilletera]:
        rows = (
            await self._s.execute(
                select(MovimientoBilleteraModel)
                .where(MovimientoBilleteraModel.id_transaccion_canje == id_transaccion)
                .order_by(MovimientoBilleteraModel.creado_en.asc())
            )
        ).scalars()
        return [_mov_to_domain(m) for m in rows]

    async def resumen_comercio(self, id_comercio: str) -> tuple[int, int]:
        # PC emitidos (acreditaciones) y canjeados (consumos) del comercio (§09.7).
        fila = (
            await self._s.execute(
                select(
                    func.coalesce(
                        func.sum(MovimientoBilleteraModel.monto).filter(
                            MovimientoBilleteraModel.tipo == TipoMovimiento.ACREDITACION.value
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(-MovimientoBilleteraModel.monto).filter(
                            MovimientoBilleteraModel.tipo == TipoMovimiento.CONSUMO.value
                        ),
                        0,
                    ),
                )
                .select_from(MovimientoBilleteraModel)
                .join(
                    BilleteraModel,
                    BilleteraModel.id == MovimientoBilleteraModel.id_billetera,
                )
                .where(
                    BilleteraModel.id_comercio == id_comercio,
                    BilleteraModel.tipo_moneda == TipoMoneda.PC.value,
                )
            )
        ).one()
        return int(fila[0]), int(fila[1])

    async def pm_en_circulacion(self) -> int:
        total = await self._s.scalar(
            select(func.coalesce(func.sum(BilleteraModel.saldo), 0)).where(
                BilleteraModel.tipo_moneda == TipoMoneda.PM.value
            )
        )
        return int(total or 0)


def _item_to_domain(m: ItemCatalogoModel) -> ItemCatalogo:
    return ItemCatalogo(
        id=EntityId(m.id),
        titulo=m.titulo,
        descripcion=m.descripcion,
        costo_pm=m.costo_pm,
        stock=m.stock,
        fecha_desde=m.fecha_desde,
        fecha_hasta=m.fecha_hasta,
        estado=EstadoItem(m.estado),
        creado_en=m.creado_en,
    )


class SqlAlchemyItemCatalogoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, item: ItemCatalogo) -> None:
        self._s.add(
            ItemCatalogoModel(
                id=item.id.value,
                titulo=item.titulo,
                descripcion=item.descripcion,
                costo_pm=item.costo_pm,
                stock=item.stock,
                fecha_desde=item.fecha_desde,
                fecha_hasta=item.fecha_hasta,
                estado=item.estado.value,
                creado_en=item.creado_en,
            )
        )
        await self._s.flush()

    async def obtener(self, id: EntityId) -> ItemCatalogo | None:
        m = await self._s.get(ItemCatalogoModel, id.value)
        return _item_to_domain(m) if m else None

    async def listar_activos(self, hoy: date) -> list[ItemCatalogo]:
        rows = (
            await self._s.execute(
                select(ItemCatalogoModel)
                .where(
                    ItemCatalogoModel.estado == EstadoItem.ACTIVO.value,
                    ItemCatalogoModel.stock > 0,
                    ItemCatalogoModel.fecha_desde <= hoy,
                    ItemCatalogoModel.fecha_hasta >= hoy,
                )
                .order_by(ItemCatalogoModel.creado_en.desc())
            )
        ).scalars()
        return [_item_to_domain(m) for m in rows]

    async def listar_todos(self) -> list[ItemCatalogo]:
        rows = (
            await self._s.execute(
                select(ItemCatalogoModel).order_by(ItemCatalogoModel.creado_en.desc())
            )
        ).scalars()
        return [_item_to_domain(m) for m in rows]

    async def reservar_stock(self, id: EntityId) -> bool:
        row = (
            await self._s.execute(
                text(
                    "UPDATE item_catalogo SET stock = stock - 1 "
                    "WHERE id = :id AND stock > 0 AND estado = 'ACTIVO' RETURNING stock"
                ),
                {"id": id.value},
            )
        ).scalar_one_or_none()
        return row is not None


class SqlAlchemyComprobanteInventarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def agregar(self, comprobante: ComprobanteInventario) -> None:
        self._s.add(
            ComprobanteInventarioModel(
                id=comprobante.id.value,
                id_item=comprobante.id_item,
                id_persona=comprobante.id_persona,
                titulo_item=comprobante.titulo_item,
                codigo=comprobante.codigo,
                costo_pm=comprobante.costo_pm,
                creado_en=comprobante.creado_en,
            )
        )
        await self._s.flush()

    async def de_persona(self, id_persona: str) -> list[ComprobanteInventario]:
        rows = (
            await self._s.execute(
                select(ComprobanteInventarioModel)
                .where(ComprobanteInventarioModel.id_persona == id_persona)
                .order_by(ComprobanteInventarioModel.creado_en.desc())
            )
        ).scalars()
        return [
            ComprobanteInventario(
                id=EntityId(m.id),
                id_item=m.id_item,
                id_persona=m.id_persona,
                titulo_item=m.titulo_item,
                codigo=m.codigo,
                costo_pm=m.costo_pm,
                creado_en=m.creado_en,
            )
            for m in rows
        ]
