"""Consulta y administración de la cuota de generación (§11.9)."""

from __future__ import annotations

from dataclasses import dataclass

from .deps import ContenidoPuertos


@dataclass(slots=True)
class EstadoCuota:
    usados: int
    cuota: int
    disponibles: int


class Creditos:
    def __init__(self, puertos: ContenidoPuertos) -> None:
        self.p = puertos

    async def estado(self, *, id_comercio: str, periodo: str) -> EstadoCuota:
        usados = await self.p.creditos.usados(id_comercio, periodo)
        extra = await self.p.creditos.extra(id_comercio, periodo)
        cuota = self.p.config.cuota_mensual + extra
        return EstadoCuota(usados=usados, cuota=cuota, disponibles=max(0, cuota - usados))

    async def otorgar_extra(self, *, id_comercio: str, periodo: str, cantidad: int) -> None:
        # §11.9: el municipio puede otorgar créditos extra puntuales en campañas.
        await self.p.creditos.otorgar_extra(id_comercio, periodo, cantidad)
        await self.p.uow.commit()
