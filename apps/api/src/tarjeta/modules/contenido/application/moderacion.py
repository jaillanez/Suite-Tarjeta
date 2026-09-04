"""Moderación de piezas (§11.6). Reusa el criterio de confianza del comercio del PASO 07:
las piezas de comercios VERIFICADO se aprueban solas; el resto entran a la cola."""

from __future__ import annotations

from tarjeta.modules.contenido.domain.errors import PiezaInexistente
from tarjeta.modules.contenido.domain.pieza import Pieza
from tarjeta.shared.domain.types import EntityId

from .deps import ContenidoPuertos


class ModeracionPiezas:
    def __init__(self, puertos: ContenidoPuertos) -> None:
        self.p = puertos

    async def cola(self) -> list[Pieza]:
        return await self.p.piezas.listar_en_moderacion()

    async def _cargar(self, id_pieza: str) -> Pieza:
        pieza = await self.p.piezas.obtener(EntityId.from_str(id_pieza))
        if pieza is None:
            raise PiezaInexistente("La pieza no existe.")
        return pieza

    async def aprobar(self, *, id_pieza: str) -> None:
        pieza = await self._cargar(id_pieza)
        pieza.aprobar()
        await self.p.piezas.guardar(pieza)
        await self.p.outbox.escribir(pieza.pull_events())
        await self.p.uow.commit()

    async def rechazar(self, *, id_pieza: str, motivo: str) -> None:
        pieza = await self._cargar(id_pieza)
        pieza.rechazar(motivo)
        await self.p.piezas.guardar(pieza)
        await self.p.outbox.escribir(pieza.pull_events())
        await self.p.uow.commit()
