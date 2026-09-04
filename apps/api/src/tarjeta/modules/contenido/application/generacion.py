"""Generación y edición de piezas (§11.4–11.9).

La reserva del crédito se confirma ANTES de llamar al proveedor (para no sostener el bloqueo de la
cuota durante una llamada lenta) y se DEVUELVE si la generación falla. Toda la composición de texto
(porcentaje/vigencia/nombre) y la edición no consumen crédito: son composición, no generación.
"""

from __future__ import annotations

import uuid

from tarjeta.modules.contenido.domain.errors import (
    CuotaAgotada,
    GeneracionFallida,
    PiezaInexistente,
)
from tarjeta.modules.contenido.domain.pieza import Pieza, Superposicion
from tarjeta.modules.contenido.domain.plantillas import obtener_plantilla
from tarjeta.modules.contenido.domain.prompt import componer_prompt
from tarjeta.modules.contenido.domain.tipos import FormatoPieza, OrigenPieza
from tarjeta.shared.domain.types import EntityId

from .deps import ContenidoPuertos


class _ServicioPieza:
    def __init__(self, puertos: ContenidoPuertos) -> None:
        self.p = puertos

    async def _componer_formatos(self, pieza: Pieza, fondo: bytes) -> None:
        """Genera y guarda los tres formatos (§11.8). No consume crédito."""
        plantilla = obtener_plantilla(pieza.plantilla)
        formatos: dict[str, str] = {}
        for formato in FormatoPieza:
            img = self.p.compositor.componer(
                fondo=fondo,
                superposicion=pieza.superposicion,
                plantilla=plantilla,
                formato=formato,
                con_marca_agua=pieza.generada_por_ia,
            )
            clave = f"pieza/{pieza.id}/{formato.value.lower()}.png"
            await self.p.almacen.guardar(clave, img, "image/png")
            formatos[formato.value] = clave
        pieza.set_formatos(formatos)

    def _moderar(self, pieza: Pieza, auto_aprueba: bool) -> None:
        # §11.6: según la confianza del comercio (la decide el composition root).
        if auto_aprueba:
            pieza.aprobar()
        else:
            pieza.enviar_a_moderacion()


class GenerarPieza(_ServicioPieza):
    async def ejecutar(
        self,
        *,
        id_comercio: str,
        id_promocion: str,
        idea: str,
        rubro: str,
        nombre_fantasia: str,
        mecanica: str,
        estilo_plantilla: str,
        superposicion: Superposicion,
        plantilla: str,
        auto_aprueba: bool,
        periodo: str,
    ) -> Pieza:
        # Reserva atómica del crédito, confirmada de inmediato (no se sostiene durante la llamada).
        usados = await self.p.creditos.reservar(id_comercio, periodo, self.p.config.cuota_mensual)
        await self.p.uow.commit()
        if usados is None:
            raise CuotaAgotada("No te quedan créditos de generación este mes.")
        prompt = componer_prompt(
            idea,
            rubro=rubro,
            nombre_fantasia=nombre_fantasia,
            mecanica=mecanica,
            estilo_plantilla=estilo_plantilla,
        )
        try:
            imagenes = await self.p.generador.generar(
                prompt, cantidad=self.p.config.variantes_por_credito, tamano=self.p.config.tamano
            )
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del proveedor devuelve el crédito
            await self.p.creditos.devolver(id_comercio, periodo)
            await self.p.uow.commit()
            raise GeneracionFallida("El proveedor falló; se devolvió el crédito.") from exc
        if not imagenes:
            await self.p.creditos.devolver(id_comercio, periodo)
            await self.p.uow.commit()
            raise GeneracionFallida("El proveedor no devolvió imágenes; se devolvió el crédito.")

        prefijo = uuid.uuid4()
        variantes: list[str] = []
        for i, img in enumerate(imagenes):
            clave = f"pieza/{prefijo}/variante-{i}.png"
            await self.p.almacen.guardar(clave, img, "image/png")
            variantes.append(clave)
        pieza = Pieza.crear(
            id_comercio=id_comercio,
            id_promocion=id_promocion,
            origen=OrigenPieza.IA,
            plantilla=plantilla,
            idea_texto=idea,
            prompt_usado=prompt,
            superposicion=superposicion,
            imagen_fondo_clave=variantes[0],
            variantes_claves=variantes,
            modelo_ia=self.p.generador.nombre,
        )
        await self._componer_formatos(pieza, imagenes[0])
        self._moderar(pieza, auto_aprueba)
        await self.p.piezas.agregar(pieza)
        await self.p.outbox.escribir(pieza.pull_events())
        await self.p.uow.commit()
        return pieza


class CrearPiezaDesdeFoto(_ServicioPieza):
    """§11.7: el camino recomendado. Foto propia + plantilla, sin crédito ni marca de agua de IA."""

    async def ejecutar(
        self,
        *,
        id_comercio: str,
        id_promocion: str,
        foto: bytes,
        superposicion: Superposicion,
        plantilla: str,
        auto_aprueba: bool,
    ) -> Pieza:
        prefijo = uuid.uuid4()
        clave_fondo = f"pieza/{prefijo}/foto.png"
        await self.p.almacen.guardar(clave_fondo, foto, "image/png")
        pieza = Pieza.crear(
            id_comercio=id_comercio,
            id_promocion=id_promocion,
            origen=OrigenPieza.FOTO_PROPIA,
            plantilla=plantilla,
            idea_texto="",
            prompt_usado="",
            superposicion=superposicion,
            imagen_fondo_clave=clave_fondo,
            variantes_claves=[clave_fondo],
            modelo_ia=None,
        )
        await self._componer_formatos(pieza, foto)
        self._moderar(pieza, auto_aprueba)
        await self.p.piezas.agregar(pieza)
        await self.p.outbox.escribir(pieza.pull_events())
        await self.p.uow.commit()
        return pieza


class RegenerarSuperposicion(_ServicioPieza):
    """§11.5: cambió el % (u otro dato) de la promoción. Recompone el texto SIN gastar crédito."""

    async def ejecutar(self, *, id_pieza: str, superposicion: Superposicion) -> Pieza:
        pieza = await self.p.piezas.obtener(EntityId.from_str(id_pieza))
        if pieza is None:
            raise PiezaInexistente("La pieza no existe.")
        pieza.actualizar_superposicion(superposicion)
        fondo = await self.p.almacen.leer(pieza.imagen_fondo_clave)
        if fondo is not None:
            await self._componer_formatos(pieza, fondo)
        await self.p.piezas.guardar(pieza)
        await self.p.uow.commit()
        return pieza


class EditarPieza(_ServicioPieza):
    """§11.8: el editor. Todo lo que se ajusta sin regenerar es un crédito que no se gasta."""

    async def cambiar_plantilla(self, *, id_pieza: str, plantilla: str) -> Pieza:
        pieza = await self.p.piezas.obtener(EntityId.from_str(id_pieza))
        if pieza is None:
            raise PiezaInexistente("La pieza no existe.")
        pieza.plantilla = plantilla
        fondo = await self.p.almacen.leer(pieza.imagen_fondo_clave)
        if fondo is not None:
            await self._componer_formatos(pieza, fondo)
        await self.p.piezas.guardar(pieza)
        await self.p.uow.commit()
        return pieza

    async def elegir_variante(self, *, id_pieza: str, indice: int) -> Pieza:
        pieza = await self.p.piezas.obtener(EntityId.from_str(id_pieza))
        if pieza is None:
            raise PiezaInexistente("La pieza no existe.")
        if 0 <= indice < len(pieza.variantes_claves):
            pieza.imagen_fondo_clave = pieza.variantes_claves[indice]
            fondo = await self.p.almacen.leer(pieza.imagen_fondo_clave)
            if fondo is not None:
                await self._componer_formatos(pieza, fondo)
            await self.p.piezas.guardar(pieza)
            await self.p.uow.commit()
        return pieza
