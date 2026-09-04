"""Integración del canje con el libro de puntos (§09.4).

Un canje acredita PC según la mecánica y, opcionalmente, consume PC que el ciudadano decide usar.
La anulación revierte todo con movimientos compensatorios, nunca editando los originales. La
acreditación es idempotente por transacción: reintentar una sincronización no acredita dos veces.
"""

from __future__ import annotations

from tarjeta.modules.puntos.domain.moneda import (
    TipoMoneda,
    puntos_comercio_por_canje,
)
from tarjeta.modules.puntos.domain.movimiento import MovimientoBilletera, TipoMovimiento
from tarjeta.shared.domain.types import EntityId

from .contabilidad import Contabilidad, sumar_meses
from .deps import PuntosPuertos


class PuntosCanjeServicio:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos
        self.conta = Contabilidad(puertos)

    async def acreditar_canje(
        self,
        *,
        id_transaccion: str,
        id_titular: str,
        id_comercio: str,
        mecanica: str,
        valor: int,
        monto: int,
    ) -> int:
        """PC que otorga el canje. Idempotente por `cred:{id_transaccion}`."""
        puntos = puntos_comercio_por_canje(
            mecanica, valor, monto, base_por_cien=self.p.config.base_por_cien
        )
        if puntos <= 0:
            return 0
        return await self.conta.acreditar(
            id_titular=id_titular,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=id_comercio,
            puntos=puntos,
            concepto="Acreditación por canje",
            id_transaccion=id_transaccion,
            clave_dedup=f"cred:{id_transaccion}",
        )

    async def consumir_canje(
        self,
        *,
        id_transaccion: str,
        id_titular: str,
        id_comercio: str,
        puntos_solicitados: int,
        tope_pesos: int,
    ) -> tuple[int, int]:
        """Consume PC para pagar. Devuelve (puntos_consumidos, pesos_cubiertos).

        Se topea al total a pagar para que el total nunca quede negativo, y a lo disponible en la
        billetera (no falla el canje si el ciudadano pide más de lo que tiene).
        """
        if puntos_solicitados <= 0 or tope_pesos <= 0:
            return (0, 0)
        vp = max(1, self.p.config.valor_punto)
        objetivo = min(puntos_solicitados, tope_pesos // vp)
        if objetivo <= 0:
            return (0, 0)
        consumido = await self.conta.consumir(
            id_titular=id_titular,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=id_comercio,
            puntos=objetivo,
            concepto="Pago con puntos",
            id_transaccion=id_transaccion,
            exigir_completo=False,
        )
        return (consumido, consumido * vp)

    async def revertir_canje(self, *, id_transaccion: str) -> None:
        """Compensa acreditación y consumo de una transacción anulada (§09.4).

        Si los puntos acreditados ya se gastaron, la reversa deja el saldo en negativo (se permite)
        y se compensa con las siguientes acumulaciones. Nunca edita el movimiento original.
        """
        movs = await self.p.movimientos.por_transaccion(id_transaccion)
        if not movs:
            return
        if await self.p.movimientos.existe(
            f"rev-cred:{id_transaccion}"
        ) or await self.p.movimientos.existe(f"rev-cons:{id_transaccion}"):
            return  # ya revertido (la anulación es una transición de una sola vez)
        id_billetera = movs[0].id_billetera
        acreditaciones = [m for m in movs if m.tipo is TipoMovimiento.ACREDITACION]
        consumos = [m for m in movs if m.tipo is TipoMovimiento.CONSUMO]
        total_cred = sum(m.monto for m in acreditaciones)
        total_cons = sum(-m.monto for m in consumos)
        ahora = movs[-1].creado_en

        if total_cred > 0:
            await self.p.movimientos.agregar(
                MovimientoBilletera(
                    id=EntityId.new(),
                    id_billetera=id_billetera,
                    tipo=TipoMovimiento.REVERSA_ACREDITACION,
                    monto=-total_cred,
                    origen_puntos=acreditaciones[0].origen_puntos,
                    creado_en=ahora,
                    id_transaccion_canje=id_transaccion,
                    clave_dedup=f"rev-cred:{id_transaccion}",
                    concepto="Reversa de acreditación por anulación",
                )
            )
            # Quita del lote acreditado lo que aún no se gastó (lo gastado ya no está).
            for m in acreditaciones:
                if m.id_lote is None:
                    continue
                lote = await self.p.lotes.obtener(m.id_lote)
                if lote is not None and lote.saldo_restante > 0:
                    await self.p.lotes.descontar(m.id_lote, min(lote.saldo_restante, m.monto))
            await self.p.billeteras.ajustar_saldo(id_billetera, -total_cred)

        if total_cons > 0:
            await self.p.movimientos.agregar(
                MovimientoBilletera(
                    id=EntityId.new(),
                    id_billetera=id_billetera,
                    tipo=TipoMovimiento.REVERSA_CONSUMO,
                    monto=total_cons,
                    origen_puntos=consumos[0].origen_puntos,
                    creado_en=ahora,
                    id_transaccion_canje=id_transaccion,
                    clave_dedup=f"rev-cons:{id_transaccion}",
                    concepto="Reversa de consumo por anulación",
                )
            )
            # Restituye los puntos gastados como un lote nuevo con vencimiento estándar.
            from tarjeta.modules.puntos.domain.lote import LotePuntos

            await self.p.lotes.agregar(
                LotePuntos(
                    id=EntityId.new(),
                    id_billetera=id_billetera,
                    monto_original=total_cons,
                    saldo_restante=total_cons,
                    vence_en=sumar_meses(ahora.date(), self.p.config.vencimiento_meses),
                    origen_puntos=consumos[0].origen_puntos,
                    creado_en=ahora,
                    id_transaccion_canje=id_transaccion,
                )
            )
            await self.p.billeteras.ajustar_saldo(id_billetera, total_cons)
