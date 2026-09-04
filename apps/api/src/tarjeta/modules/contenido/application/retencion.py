"""Política de retención (§11.10): las piezas de promociones vencidas hace mucho liberan sus
objetos para que el almacenamiento no crezca sin techo. La fila queda como registro (tombstone);
lo pesado (las imágenes) se borra."""

from __future__ import annotations

from tarjeta.shared.domain.types import EntityId

from .deps import ContenidoPuertos


class Retencion:
    def __init__(self, puertos: ContenidoPuertos) -> None:
        self.p = puertos

    async def purgar_pieza(self, *, id_pieza: str) -> bool:
        pieza = await self.p.piezas.obtener(EntityId.from_str(id_pieza))
        if pieza is None:
            return False
        claves = {pieza.imagen_fondo_clave, *pieza.variantes_claves, *pieza.formatos.values()}
        for clave in claves:
            await self.p.almacen.borrar(clave)
        pieza.set_formatos({})
        await self.p.piezas.guardar(pieza)
        await self.p.uow.commit()
        return True

    async def purgar_de_promociones(self, ids_promociones: list[str]) -> int:
        """El composition root pasa las promociones vencidas hace mucho (las conoce el módulo)."""
        borradas = 0
        for id_promocion in ids_promociones:
            for pieza in await self.p.piezas.de_promocion(id_promocion):
                if await self.purgar_pieza(id_pieza=str(pieza.id)):
                    borradas += 1
        return borradas
