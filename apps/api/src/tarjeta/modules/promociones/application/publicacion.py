"""Publicación y moderación de promociones (§07.5)."""

from __future__ import annotations

from tarjeta.modules.promociones.domain.confianza import (
    PerfilConfianza,
    requiere_revision_previa,
)
from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import PromocionesPuertos


class PublicarPromocion:
    """El comercio envía la promoción; se auto-publica o va a revisión según su confianza."""

    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def ejecutar(
        self,
        *,
        id_promocion: str,
        id_comercio: str,
        umbral_establecido: int,
        umbral_verificado: int,
    ) -> str:
        promo = await self.p.promociones.obtener(EntityId.from_str(id_promocion))
        if promo is None or str(promo.id_comercio) != id_comercio:
            raise NotFoundError("Promoción inexistente.")
        perfil = await self._perfil(id_comercio)
        if requiere_revision_previa(perfil.nivel):
            promo.enviar_a_revision()
        else:
            # ESTABLECIDO/VERIFICADO publican sin revisión previa (§4.4).
            promo.activar()
        await self.p.promociones.guardar(promo)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()
        return promo.estado.value

    async def _perfil(self, id_comercio: str) -> PerfilConfianza:
        pid = EntityId.from_str(id_comercio)
        perfil = await self.p.confianza.obtener(pid)
        if perfil is None:
            perfil = PerfilConfianza(id=pid)
            await self.p.confianza.guardar(perfil)
        return perfil


class ModerarPromocion:
    """Cola municipal: aprobar (con o sin edición) o rechazar (§07.5)."""

    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def _cargar(self, id_promocion: str) -> Promocion:
        promo = await self.p.promociones.obtener(EntityId.from_str(id_promocion))
        if promo is None:
            raise NotFoundError("Promoción inexistente.")
        return promo

    async def aprobar(
        self, *, id_promocion: str, umbral_establecido: int, umbral_verificado: int
    ) -> None:
        promo = await self._cargar(id_promocion)
        promo.aprobar()
        promo.activar()
        await self.p.promociones.guardar(promo)
        await self._sumar_confianza(promo, umbral_establecido, umbral_verificado)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()

    async def aprobar_con_edicion(
        self,
        *,
        id_promocion: str,
        titulo: str,
        descripcion: str,
        imagen_url: str,
        umbral_establecido: int,
        umbral_verificado: int,
    ) -> None:
        promo = await self._cargar(id_promocion)
        promo.editar_presentacion(titulo=titulo, descripcion=descripcion, imagen_url=imagen_url)
        promo.aprobar()
        promo.activar()
        await self.p.promociones.guardar(promo)
        await self._sumar_confianza(promo, umbral_establecido, umbral_verificado)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()

    async def rechazar(self, *, id_promocion: str, motivo: str) -> None:
        promo = await self._cargar(id_promocion)
        promo.rechazar(motivo)
        await self.p.promociones.guardar(promo)
        await self.p.outbox.escribir(promo.pull_events())
        await self.p.uow.commit()

    async def _sumar_confianza(
        self, promo: Promocion, umbral_establecido: int, umbral_verificado: int
    ) -> None:
        pid = promo.id_comercio
        perfil = await self.p.confianza.obtener(pid) or PerfilConfianza(id=pid)
        perfil.registrar_aprobacion(
            umbral_establecido=umbral_establecido, umbral_verificado=umbral_verificado
        )
        await self.p.confianza.guardar(perfil)
        await self.p.outbox.escribir(perfil.pull_events())
