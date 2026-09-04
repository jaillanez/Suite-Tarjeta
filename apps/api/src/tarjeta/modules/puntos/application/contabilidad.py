"""Primitivas del libro contable: acreditar, consumir (FIFO), verificar (§09.2).

Todo cambio de saldo pasa por acá y siempre queda como un movimiento nuevo en el libro. El saldo
de la billetera se ajusta atómicamente en la base dentro de la misma transacción que crea el
movimiento; nunca se edita un movimiento existente.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime

from tarjeta.modules.puntos.domain.billetera import Billetera
from tarjeta.modules.puntos.domain.errors import SaldoInsuficiente
from tarjeta.modules.puntos.domain.lote import LotePuntos
from tarjeta.modules.puntos.domain.moneda import OrigenPuntos, TipoMoneda, TipoTitular
from tarjeta.modules.puntos.domain.movimiento import MovimientoBilletera, TipoMovimiento
from tarjeta.shared.domain.types import EntityId

from .deps import PuntosConfig, PuntosPuertos


def sumar_meses(base: date, meses: int) -> date:
    """Suma meses a una fecha, recortando el día al último válido del mes destino."""
    total = base.month - 1 + meses
    anio = base.year + total // 12
    mes = total % 12 + 1
    dia = min(base.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


class Contabilidad:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos

    @property
    def cfg(self) -> PuntosConfig:
        return self.p.config

    async def _billetera(
        self,
        *,
        tipo_titular: TipoTitular,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
    ) -> Billetera:
        return await self.p.billeteras.obtener_o_crear(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=tipo_moneda,
            id_comercio=id_comercio,
        )

    async def acreditar(
        self,
        *,
        tipo_titular: TipoTitular = TipoTitular.PERSONA,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
        puntos: int,
        origen: OrigenPuntos = OrigenPuntos.INDIVIDUAL,
        concepto: str,
        id_transaccion: str | None = None,
        clave_dedup: str | None = None,
        vence_en: date | None = None,
    ) -> int:
        """Acredita `puntos` en un lote nuevo. Idempotente por `clave_dedup` (§09.4)."""
        if puntos <= 0:
            return 0
        b = await self._billetera(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=tipo_moneda,
            id_comercio=id_comercio,
        )
        # La verificación de duplicado va DESPUÉS del lock de la billetera (evita doble crédito
        # bajo dos sincronizaciones simultáneas).
        if clave_dedup and await self.p.movimientos.existe(clave_dedup):
            return 0
        ahora = datetime.now(UTC)
        vence = vence_en or sumar_meses(ahora.date(), self.cfg.vencimiento_meses)
        lote = LotePuntos(
            id=EntityId.new(),
            id_billetera=b.id,
            monto_original=puntos,
            saldo_restante=puntos,
            vence_en=vence,
            origen_puntos=origen,
            creado_en=ahora,
            id_transaccion_canje=id_transaccion,
        )
        await self.p.lotes.agregar(lote)
        await self.p.movimientos.agregar(
            MovimientoBilletera(
                id=EntityId.new(),
                id_billetera=b.id,
                tipo=TipoMovimiento.ACREDITACION,
                monto=puntos,
                origen_puntos=origen,
                creado_en=ahora,
                id_lote=lote.id,
                id_transaccion_canje=id_transaccion,
                clave_dedup=clave_dedup,
                concepto=concepto,
            )
        )
        await self.p.billeteras.ajustar_saldo(b.id, puntos)
        return puntos

    async def consumir(
        self,
        *,
        tipo_titular: TipoTitular = TipoTitular.PERSONA,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
        puntos: int,
        concepto: str,
        id_transaccion: str | None = None,
        exigir_completo: bool = True,
    ) -> int:
        """Consume puntos empezando por el lote más viejo (FIFO por vencimiento, §09.2).

        Con `exigir_completo` lanza SaldoInsuficiente si no alcanza; si no, consume lo disponible
        y devuelve cuánto consumió (lo usa el canje para topear al total a pagar).
        """
        if puntos <= 0:
            return 0
        b = await self._billetera(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=tipo_moneda,
            id_comercio=id_comercio,
        )
        hoy = datetime.now(UTC).date()
        lotes = await self.p.lotes.disponibles_fifo(b.id, hoy)
        disponible = sum(lote.saldo_restante for lote in lotes)
        if exigir_completo and disponible < puntos:
            raise SaldoInsuficiente("No hay puntos suficientes para el consumo.")
        restante = min(puntos, disponible)
        consumido = 0
        ahora = datetime.now(UTC)
        for lote in lotes:
            if restante <= 0:
                break
            toma = min(lote.saldo_restante, restante)
            await self.p.lotes.descontar(lote.id, toma)
            await self.p.movimientos.agregar(
                MovimientoBilletera(
                    id=EntityId.new(),
                    id_billetera=b.id,
                    tipo=TipoMovimiento.CONSUMO,
                    monto=-toma,
                    origen_puntos=lote.origen_puntos,
                    creado_en=ahora,
                    id_lote=lote.id,
                    id_transaccion_canje=id_transaccion,
                    concepto=concepto,
                )
            )
            await self.p.billeteras.ajustar_saldo(b.id, -toma)
            restante -= toma
            consumido += toma
        return consumido

    async def saldo_libro(self, id_billetera: EntityId) -> int:
        """Saldo reconstruido desde el libro (para la verificación de consistencia, §09.2)."""
        return await self.p.movimientos.suma(id_billetera)
