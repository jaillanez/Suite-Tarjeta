"""Lecturas de billeteras: saldos, movimientos, lotes por vencer y verificación (§09.2, §09.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from tarjeta.modules.puntos.domain.billetera import Billetera
from tarjeta.modules.puntos.domain.moneda import TipoMoneda, TipoTitular
from tarjeta.modules.puntos.domain.movimiento import MovimientoBilletera

from .deps import PuntosPuertos


@dataclass(slots=True)
class SaldoComercio:
    id_comercio: str
    saldo: int


@dataclass(slots=True)
class ResumenBilleteras:
    # PC nunca se mezcla con PM: dos billeteras visualmente separadas (§09.7).
    pc: list[SaldoComercio] = field(default_factory=list)
    pm: int = 0


@dataclass(slots=True)
class LotePorVencer:
    tipo_moneda: str
    id_comercio: str
    saldo_restante: int
    vence_en: str
    dias_restantes: int


class ConsultaBilleteras:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos

    async def resumen(
        self, id_titular: str, *, tipo_titular: TipoTitular = TipoTitular.PERSONA
    ) -> ResumenBilleteras:
        pc = [
            SaldoComercio(id_comercio=b.id_comercio, saldo=b.saldo)
            for b in await self.p.billeteras.pc_de_titular(id_titular)
        ]
        pm_bill = await self.p.billeteras.obtener(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
        )
        return ResumenBilleteras(pc=pc, pm=pm_bill.saldo if pm_bill else 0)

    async def movimientos(
        self,
        id_titular: str,
        *,
        tipo_moneda: str,
        id_comercio: str | None,
        tipo_titular: TipoTitular = TipoTitular.PERSONA,
        limite: int = 100,
    ) -> list[MovimientoBilletera]:
        b = await self.p.billeteras.obtener(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=TipoMoneda(tipo_moneda),
            id_comercio=id_comercio,
        )
        if b is None:
            return []
        return await self.p.movimientos.listar(b.id, limite)

    async def _billeteras_de(self, id_titular: str, tipo_titular: TipoTitular) -> list[Billetera]:
        billeteras = list(await self.p.billeteras.pc_de_titular(id_titular))
        pm = await self.p.billeteras.obtener(
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
        )
        if pm is not None:
            billeteras.append(pm)
        return billeteras

    async def por_vencer(
        self, id_titular: str, *, dias: int = 30, tipo_titular: TipoTitular = TipoTitular.PERSONA
    ) -> list[LotePorVencer]:
        hoy = datetime.now(UTC).date()
        hasta = hoy + timedelta(days=dias)
        salida: list[LotePorVencer] = []
        for b in await self._billeteras_de(id_titular, tipo_titular):
            for lote in await self.p.lotes.por_vencer(b.id, hoy, hasta):
                salida.append(
                    LotePorVencer(
                        tipo_moneda=b.tipo_moneda.value,
                        id_comercio=b.id_comercio,
                        saldo_restante=lote.saldo_restante,
                        vence_en=lote.vence_en.isoformat(),
                        dias_restantes=(lote.vence_en - hoy).days,
                    )
                )
        salida.sort(key=lambda x: x.dias_restantes)
        return salida

    async def verificar_consistencia(
        self, id_titular: str, *, tipo_titular: TipoTitular = TipoTitular.PERSONA
    ) -> bool:
        """Cada saldo debe coincidir con la suma de su libro (§09.2)."""
        for b in await self._billeteras_de(id_titular, tipo_titular):
            if b.saldo != await self.p.movimientos.suma(b.id):
                return False
        return True
