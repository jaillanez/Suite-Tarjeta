"""Gestión de promociones del lado del comercio (§07.2, §07.8)."""

from __future__ import annotations

from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento
from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.modules.promociones.domain.vigencia import Vigencia
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import PromocionesPuertos


class GestionPromociones:
    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def crear(
        self,
        *,
        id_comercio: str,
        titulo: str,
        descripcion: str,
        mecanica: Mecanica,
        segmento: Segmento,
        valor_platino: int | None,
        valor_black: int,
        vigencia: Vigencia,
        sucursales: list[str],
        acumulable: bool = False,
        tope_total: int | None = None,
        tope_por_usuario: int | None = None,
        tope_por_dia: int | None = None,
        monto_minimo: int = 0,
        imagen_url: str = "",
    ) -> str:
        promo = Promocion.crear(
            id_comercio=EntityId.from_str(id_comercio),
            titulo=titulo,
            descripcion=descripcion,
            mecanica=mecanica,
            segmento=segmento,
            valor_platino=valor_platino,
            valor_black=valor_black,
            vigencia=vigencia,
            sucursales=[EntityId.from_str(s) for s in sucursales],
            acumulable=acumulable,
            tope_total=tope_total,
            tope_por_usuario=tope_por_usuario,
            tope_por_dia=tope_por_dia,
            monto_minimo=monto_minimo,
            imagen_url=imagen_url,
        )
        await self.p.promociones.agregar(promo)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()
        return str(promo.id)

    async def _cargar(self, id_promocion: str, id_comercio: str) -> Promocion:
        promo = await self.p.promociones.obtener(EntityId.from_str(id_promocion))
        if promo is None or str(promo.id_comercio) != id_comercio:
            raise NotFoundError("Promoción inexistente.")
        return promo

    async def editar_condiciones(
        self,
        *,
        id_promocion: str,
        id_comercio: str,
        mecanica: Mecanica,
        valor_platino: int | None,
        valor_black: int,
        tope_total: int | None,
    ) -> None:
        promo = await self._cargar(id_promocion, id_comercio)
        promo.editar_condiciones_economicas(
            mecanica=mecanica,
            valor_platino=valor_platino,
            valor_black=valor_black,
            tope_total=tope_total,
        )
        await self.p.promociones.guardar(promo)
        await self.p.uow.commit()

    async def pausar(self, *, id_promocion: str, id_comercio: str) -> None:
        promo = await self._cargar(id_promocion, id_comercio)
        promo.pausar()
        await self.p.promociones.guardar(promo)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()

    async def reanudar(self, *, id_promocion: str, id_comercio: str) -> None:
        promo = await self._cargar(id_promocion, id_comercio)
        promo.reanudar()
        await self.p.promociones.guardar(promo)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()

    async def duplicar(self, *, id_promocion: str, id_comercio: str) -> str:
        base = await self._cargar(id_promocion, id_comercio)
        return await self.crear(
            id_comercio=id_comercio,
            titulo=f"{base.titulo} (copia)",
            descripcion=base.descripcion,
            mecanica=base.mecanica,
            segmento=base.segmento,
            valor_platino=base.valor_platino,
            valor_black=base.valor_black,
            vigencia=base.vigencia,
            sucursales=[str(s) for s in base.sucursales],
            acumulable=base.acumulable,
            tope_total=base.tope_total,
            tope_por_usuario=base.tope_por_usuario,
            tope_por_dia=base.tope_por_dia,
            monto_minimo=base.monto_minimo,
            imagen_url=base.imagen_url,
        )
