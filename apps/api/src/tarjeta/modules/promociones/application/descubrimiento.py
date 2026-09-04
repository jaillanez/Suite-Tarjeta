"""Descubrimiento: buscador, feed y favoritos (§07.6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tarjeta.modules.promociones.domain.ports import CriteriosBusqueda
from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.shared.domain.types import EntityId

from .deps import PromocionesPuertos


class Descubrimiento:
    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def buscar(self, criterios: CriteriosBusqueda) -> list[Promocion]:
        return await self.p.promociones.buscar(criterios)

    async def nuevas_esta_semana(self, limite: int = 20) -> list[Promocion]:
        desde = datetime.now(UTC) - timedelta(days=7)
        return await self.p.promociones.nuevas_desde(desde, limite)

    async def vencen_pronto(self, dias: int = 7, limite: int = 20) -> list[Promocion]:
        hasta = (datetime.now(UTC) + timedelta(days=dias)).date()
        return await self.p.promociones.vencen_antes_de(hasta, limite)

    async def exclusivas_black(self, limite: int = 20) -> list[Promocion]:
        # §3.5: si el vecino es Platino, el composition root las muestra bloqueadas (% visible).
        return await self.p.promociones.exclusivas_black(limite)

    # --- favoritos ------------------------------------------------------------
    async def marcar_favorito(
        self, *, id_persona: str, comercio: str = "", rubro: str = ""
    ) -> None:
        await self.p.favoritos.agregar(
            EntityId.from_str(id_persona), comercio=comercio, rubro=rubro
        )
        await self.p.uow.commit()

    async def quitar_favorito(
        self, *, id_persona: str, comercio: str = "", rubro: str = ""
    ) -> None:
        await self.p.favoritos.quitar(EntityId.from_str(id_persona), comercio=comercio, rubro=rubro)
        await self.p.uow.commit()

    async def favoritos_de(self, *, id_persona: str) -> dict[str, list[str]]:
        pid = EntityId.from_str(id_persona)
        return {
            "comercios": await self.p.favoritos.comercios_de(pid),
            "rubros": await self.p.favoritos.rubros_de(pid),
        }
