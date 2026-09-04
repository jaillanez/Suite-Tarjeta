"""Repositorios del módulo canje."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.canje.domain.ports import ResumenTurno
from tarjeta.modules.canje.domain.transaccion import (
    Confirmador,
    EstadoTransaccion,
    Transaccion,
    ViaCanje,
)
from tarjeta.shared.domain.types import EntityId

from .models import TransaccionModel


def _to_domain(m: TransaccionModel) -> Transaccion:
    return Transaccion(
        id=EntityId(m.id),
        numero_comprobante=m.numero_comprobante,
        id_persona=m.id_persona,
        nivel_aplicado=m.nivel_aplicado,
        id_comercio=m.id_comercio,
        id_sucursal=m.id_sucursal,
        id_cajero=m.id_cajero,
        id_promocion=m.id_promocion,
        monto_bruto=m.monto_bruto,
        descuento=m.descuento,
        via=ViaCanje(m.via),
        confirmador=Confirmador(m.confirmador),
        estado=EstadoTransaccion(m.estado),
        clave_idempotencia=m.clave_idempotencia,
        vence_en=m.vence_en,
        creada_en=m.creada_en,
        confirmada_en=m.confirmada_en,
        sin_conexion=m.sin_conexion,
        geo_lat=m.geo_lat,
        geo_lon=m.geo_lon,
        distancia_m=m.distancia_m,
        calificacion=m.calificacion,
        motivo_anulacion=m.motivo_anulacion,
        en_disputa=m.en_disputa,
        puntos_ciudadano=m.puntos_ciudadano,
        puntos_municipio=m.puntos_municipio,
        puntos_consumidos=m.puntos_consumidos,
        pesos_cubiertos_puntos=m.pesos_cubiertos_puntos,
    )


class SqlAlchemyTransaccionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, t: Transaccion) -> TransaccionModel:
        return TransaccionModel(
            id=t.id.value,
            numero_comprobante=t.numero_comprobante,
            id_persona=t.id_persona,
            nivel_aplicado=t.nivel_aplicado,
            id_comercio=t.id_comercio,
            id_sucursal=t.id_sucursal,
            id_cajero=t.id_cajero,
            id_promocion=t.id_promocion,
            monto_bruto=t.monto_bruto,
            descuento=t.descuento,
            via=t.via.value,
            confirmador=t.confirmador.value,
            estado=t.estado.value,
            clave_idempotencia=t.clave_idempotencia,
            vence_en=t.vence_en,
            creada_en=t.creada_en,
            confirmada_en=t.confirmada_en,
            sin_conexion=t.sin_conexion,
            geo_lat=t.geo_lat,
            geo_lon=t.geo_lon,
            distancia_m=t.distancia_m,
            calificacion=t.calificacion,
            motivo_anulacion=t.motivo_anulacion,
            en_disputa=t.en_disputa,
            puntos_ciudadano=t.puntos_ciudadano,
            puntos_municipio=t.puntos_municipio,
            puntos_consumidos=t.puntos_consumidos,
            pesos_cubiertos_puntos=t.pesos_cubiertos_puntos,
        )

    async def agregar(self, t: Transaccion) -> None:
        self._s.add(self._to_model(t))
        await self._s.flush()

    async def guardar(self, t: Transaccion) -> None:
        m = await self._s.get(TransaccionModel, t.id.value)
        if m is None:
            return
        m.estado = t.estado.value
        m.descuento = t.descuento
        m.confirmada_en = t.confirmada_en
        m.calificacion = t.calificacion
        m.motivo_anulacion = t.motivo_anulacion
        m.en_disputa = t.en_disputa
        m.puntos_ciudadano = t.puntos_ciudadano
        m.puntos_consumidos = t.puntos_consumidos
        m.pesos_cubiertos_puntos = t.pesos_cubiertos_puntos

    async def obtener(self, id: EntityId) -> Transaccion | None:
        m = await self._s.get(TransaccionModel, id.value)
        return _to_domain(m) if m else None

    async def por_idempotencia(self, clave: str) -> Transaccion | None:
        m = await self._s.scalar(
            select(TransaccionModel).where(TransaccionModel.clave_idempotencia == clave)
        )
        return _to_domain(m) if m else None

    async def _listar(self, *filtros: Any) -> list[Transaccion]:
        rows = (
            await self._s.execute(
                select(TransaccionModel).where(*filtros).order_by(TransaccionModel.creada_en.desc())
            )
        ).scalars()
        return [_to_domain(m) for m in rows]

    async def pendientes_de_persona(self, id_persona: str) -> list[Transaccion]:
        return await self._listar(
            TransaccionModel.id_persona == id_persona,
            TransaccionModel.estado == EstadoTransaccion.PENDIENTE_CONFIRMACION.value,
        )

    async def pendientes_de_comercio(self, id_comercio: str) -> list[Transaccion]:
        return await self._listar(
            TransaccionModel.id_comercio == id_comercio,
            TransaccionModel.estado == EstadoTransaccion.PENDIENTE_CONFIRMACION.value,
        )

    async def vencidas(self, ahora: datetime) -> list[Transaccion]:
        return await self._listar(
            TransaccionModel.estado == EstadoTransaccion.PENDIENTE_CONFIRMACION.value,
            TransaccionModel.vence_en < ahora,
        )

    async def historial_de_persona(self, id_persona: str, limite: int) -> list[Transaccion]:
        rows = (
            await self._s.execute(
                select(TransaccionModel)
                .where(TransaccionModel.id_persona == id_persona)
                .order_by(TransaccionModel.creada_en.desc())
                .limit(limite)
            )
        ).scalars()
        return [_to_domain(m) for m in rows]

    async def resumen_cajero(self, id_cajero: str, desde: datetime) -> ResumenTurno:
        base = (
            TransaccionModel.id_cajero == id_cajero,
            TransaccionModel.estado == EstadoTransaccion.APLICADA.value,
            TransaccionModel.confirmada_en >= desde,
        )
        fila = (
            await self._s.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(TransaccionModel.monto_bruto), 0),
                    func.coalesce(func.sum(TransaccionModel.descuento), 0),
                ).where(*base)
            )
        ).one()
        por_promo = (
            await self._s.execute(
                select(
                    TransaccionModel.id_promocion,
                    func.coalesce(func.sum(TransaccionModel.descuento), 0),
                )
                .where(*base, TransaccionModel.id_promocion.is_not(None))
                .group_by(TransaccionModel.id_promocion)
            )
        ).all()
        return ResumenTurno(
            operaciones=int(fila[0]),
            monto_bruto=int(fila[1]),
            descuento=int(fila[2]),
            por_promocion={str(pid): int(desc) for pid, desc in por_promo},
        )


class SqlAlchemyComprobanteSecuencia:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def siguiente(self) -> int:
        val = await self._s.scalar(text("SELECT nextval('comprobante_seq')"))
        return int(val or 0)
