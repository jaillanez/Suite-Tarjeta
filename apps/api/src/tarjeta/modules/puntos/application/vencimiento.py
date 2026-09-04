"""Vencimiento de lotes cumplidos (§09.6).

Proceso periódico e idempotente: cada lote se vence una sola vez (se marca `vencido` y hay una
clave de deduplicación por lote), así correrlo dos veces el mismo día no vence dos veces. El aviso
al vecino a 30 y 7 días queda visible en la app (ver `consulta.por_vencer`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.puntos.domain.events import PuntosVencidos

from .deps import PuntosPuertos


class VencerLotes:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, limite: int = 500) -> int:
        hoy = datetime.now(UTC).date()
        lotes = await self.p.lotes.vencidos_pendientes(hoy, limite)
        vencidos = 0
        for lote in lotes:
            clave = f"venc:{lote.id}"
            if await self.p.movimientos.existe(clave):
                continue
            monto = lote.saldo_restante
            if monto <= 0:
                await self.p.lotes.marcar_vencido(lote.id)
                continue
            from tarjeta.modules.puntos.domain.movimiento import (
                MovimientoBilletera,
                TipoMovimiento,
            )
            from tarjeta.shared.domain.types import EntityId

            await self.p.lotes.marcar_vencido(lote.id)
            await self.p.movimientos.agregar(
                MovimientoBilletera(
                    id=EntityId.new(),
                    id_billetera=lote.id_billetera,
                    tipo=TipoMovimiento.VENCIMIENTO,
                    monto=-monto,
                    origen_puntos=lote.origen_puntos,
                    creado_en=datetime.now(UTC),
                    id_lote=lote.id,
                    clave_dedup=clave,
                    concepto="Vencimiento de puntos",
                )
            )
            await self.p.billeteras.ajustar_saldo(lote.id_billetera, -monto)
            billetera = await self.p.billeteras.por_id(lote.id_billetera)
            if billetera is not None:
                await self.p.outbox.escribir(
                    [
                        PuntosVencidos(
                            id_titular=billetera.id_titular,
                            tipo_moneda=billetera.tipo_moneda.value,
                            id_comercio=billetera.id_comercio,
                            puntos=monto,
                        )
                    ]
                )
            vencidos += 1
        await self.p.uow.commit()
        return vencidos
