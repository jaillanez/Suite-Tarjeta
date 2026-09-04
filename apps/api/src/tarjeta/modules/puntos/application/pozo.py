"""Traspaso del pozo común al titular (§10.5).

Al pasar de modo COMÚN a INDIVIDUAL, el pozo del grupo queda en el titular. Se mueve el saldo de
cada billetera del grupo (PC por comercio y PM) a la billetera personal del titular, como
movimientos del libro (consumo en el pozo + acreditación en el titular), sin editar nada.

NO confirma la transacción: lo hace el composition root para que el cambio de modo y el traspaso
sean atómicos.
"""

from __future__ import annotations

from tarjeta.modules.puntos.domain.moneda import OrigenPuntos, TipoMoneda, TipoTitular

from .contabilidad import Contabilidad
from .deps import PuntosPuertos


class TraspasarPozo:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos
        self.conta = Contabilidad(puertos)

    async def _mover(
        self, *, id_grupo: str, id_titular: str, tipo_moneda: TipoMoneda, id_comercio: str | None
    ) -> None:
        pozo = await self.p.billeteras.obtener(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=id_grupo,
            tipo_moneda=tipo_moneda,
            id_comercio=id_comercio,
        )
        if pozo is None or pozo.saldo <= 0:
            return
        consumido = await self.conta.consumir(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=id_grupo,
            tipo_moneda=tipo_moneda,
            id_comercio=id_comercio,
            puntos=pozo.saldo,
            concepto="Traspaso de pozo al titular",
            exigir_completo=False,
        )
        if consumido > 0:
            await self.conta.acreditar(
                tipo_titular=TipoTitular.PERSONA,
                id_titular=id_titular,
                tipo_moneda=tipo_moneda,
                id_comercio=id_comercio,
                puntos=consumido,
                origen=OrigenPuntos.INDIVIDUAL,
                concepto="Traspaso de pozo del grupo",
            )

    async def al_titular(self, *, id_grupo: str, id_titular: str) -> None:
        # PC: circuito cerrado, un pozo por comercio.
        for w in await self.p.billeteras.pc_de_titular(id_grupo):
            await self._mover(
                id_grupo=id_grupo,
                id_titular=id_titular,
                tipo_moneda=TipoMoneda.PC,
                id_comercio=w.id_comercio,
            )
        # PM del pozo.
        await self._mover(
            id_grupo=id_grupo, id_titular=id_titular, tipo_moneda=TipoMoneda.PM, id_comercio=None
        )
