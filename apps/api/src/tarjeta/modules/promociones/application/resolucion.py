"""Motor de resolución de promociones (§07.4, M0.4).

Entrada: nivel del ciudadano, sucursal, momento (hora local), monto. Salida: promociones
aplicables ordenadas por beneficio para el ciudadano. La regla de conflicto es configurable
(por defecto, mayor beneficio); nunca se aplican dos salvo que ambas sean acumulables.
"""

from __future__ import annotations

from datetime import datetime

from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.shared.domain.types import EntityId

from .deps import PromocionesPuertos

REGLA_MAYOR_BENEFICIO = "mayor_beneficio"


class MotorResolucion:
    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def resolver(
        self,
        *,
        nivel: str,
        id_sucursal: str,
        momento_local: datetime,
        monto: int = 0,
        regla: str = REGLA_MAYOR_BENEFICIO,
    ) -> list[Promocion]:
        candidatas = await self.p.promociones.candidatas(
            id_sucursal=EntityId.from_str(id_sucursal),
            nivel=nivel,
            momento_local=momento_local,
            monto=monto,
        )
        # Filtro fino que no conviene hacer en SQL: vigencia por día/franja en hora local.
        aplicables = [
            promo
            for promo in candidatas
            if promo.aplica_a_nivel(nivel) and promo.vigencia.vigente_en(momento_local)
        ]
        aplicables.sort(key=lambda pr: pr.beneficio_para(nivel), reverse=True)
        return aplicables

    async def proponer(
        self, *, nivel: str, id_sucursal: str, momento_local: datetime, monto: int = 0
    ) -> list[Promocion]:
        """La propuesta: la de mayor beneficio + las acumulables (§07.4)."""
        ordenadas = await self.resolver(
            nivel=nivel, id_sucursal=id_sucursal, momento_local=momento_local, monto=monto
        )
        if not ordenadas:
            return []
        propuestas = [ordenadas[0]]
        propuestas += [pr for pr in ordenadas[1:] if pr.acumulable]
        return propuestas
