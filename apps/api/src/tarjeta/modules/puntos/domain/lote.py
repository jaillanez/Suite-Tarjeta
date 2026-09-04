"""Lotes de puntos con vencimiento propio y consumo FIFO (§09.2).

Los puntos se acreditan por lotes con vencimiento propio y se consumen empezando por el lote
más viejo. Sin esto aparece el reclamo de "me vencieron puntos que gané ayer". El `saldo_restante`
del lote se mantiene con disciplina atómica (se descuenta en la base, no leído-y-sumado en Python).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from tarjeta.shared.domain.types import EntityId

from .moneda import OrigenPuntos


@dataclass(slots=True)
class LotePuntos:
    id: EntityId
    id_billetera: EntityId
    monto_original: int
    saldo_restante: int
    vence_en: date
    origen_puntos: OrigenPuntos
    creado_en: datetime
    id_transaccion_canje: str | None = None
    vencido: bool = False

    def disponible(self, hoy: date) -> bool:
        return not self.vencido and self.saldo_restante > 0 and self.vence_en >= hoy
