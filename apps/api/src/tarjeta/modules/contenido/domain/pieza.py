"""Agregado Pieza: una pieza gráfica de una promoción (§11).

El porcentaje/vigencia/nombre NO los genera la IA: son datos superpuestos desde la promoción con
tipografía controlada (§11.5). La IA (cuando se usa) aporta solo el fondo. Una pieza rechazada es
terminal: no puede publicarse por ningún camino (§11.6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import TransicionPiezaInvalida
from .events import PiezaAprobada, PiezaEnviadaAModeracion, PiezaGenerada, PiezaRechazada
from .tipos import EstadoPieza, OrigenPieza


@dataclass(frozen=True, slots=True)
class Superposicion:
    """Texto que se compone sobre la imagen, siempre desde los datos de la promoción."""

    porcentaje: str
    vigencia: str
    nombre: str


class Pieza(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_comercio: str,
        id_promocion: str,
        origen: OrigenPieza,
        estado: EstadoPieza,
        plantilla: str,
        idea_texto: str,
        prompt_usado: str,
        superposicion: Superposicion,
        imagen_fondo_clave: str,
        variantes_claves: list[str],
        formatos: dict[str, str],
        generada_por_ia: bool,
        modelo_ia: str | None,
        creado_en: datetime,
    ) -> None:
        super().__init__(id)
        self.id_comercio = id_comercio
        self.id_promocion = id_promocion
        self.origen = origen
        self._estado = estado
        self.plantilla = plantilla
        self.idea_texto = idea_texto
        self.prompt_usado = prompt_usado
        self.superposicion = superposicion
        self.imagen_fondo_clave = imagen_fondo_clave
        self.variantes_claves = variantes_claves
        self.formatos = formatos
        self.generada_por_ia = generada_por_ia
        self.modelo_ia = modelo_ia
        self.creado_en = creado_en

    @property
    def estado(self) -> EstadoPieza:
        return self._estado

    @property
    def publicable(self) -> bool:
        return self._estado is EstadoPieza.APROBADA

    @classmethod
    def crear(
        cls,
        *,
        id_comercio: str,
        id_promocion: str,
        origen: OrigenPieza,
        plantilla: str,
        idea_texto: str,
        prompt_usado: str,
        superposicion: Superposicion,
        imagen_fondo_clave: str,
        variantes_claves: list[str],
        modelo_ia: str | None,
    ) -> Pieza:
        pieza = cls(
            id=EntityId.new(),
            id_comercio=id_comercio,
            id_promocion=id_promocion,
            origen=origen,
            estado=EstadoPieza.BORRADOR,
            plantilla=plantilla,
            idea_texto=idea_texto,
            prompt_usado=prompt_usado,
            superposicion=superposicion,
            imagen_fondo_clave=imagen_fondo_clave,
            variantes_claves=variantes_claves,
            formatos={},
            generada_por_ia=origen is OrigenPieza.IA,
            modelo_ia=modelo_ia,
            creado_en=datetime.now(UTC),
        )
        pieza.record_event(
            PiezaGenerada(id_pieza=str(pieza.id), id_comercio=id_comercio, origen=origen.value)
        )
        return pieza

    def set_formatos(self, formatos: dict[str, str]) -> None:
        self.formatos = formatos

    def actualizar_superposicion(self, nueva: Superposicion) -> None:
        # §11.5: recomponer el texto (p. ej. cambió el %) NO cambia el estado ni consume crédito.
        self.superposicion = nueva

    def enviar_a_moderacion(self) -> None:
        if self._estado is not EstadoPieza.BORRADOR:
            raise TransicionPiezaInvalida("La pieza no está en borrador.")
        self._estado = EstadoPieza.EN_MODERACION
        self.record_event(
            PiezaEnviadaAModeracion(id_pieza=str(self.id), id_comercio=self.id_comercio)
        )

    def aprobar(self) -> None:
        # Aprueba desde borrador (confianza VERIFICADO) o desde la cola de moderación. Nunca desde
        # RECHAZADA: una pieza rechazada no vuelve a ser publicable (§11.6).
        if self._estado not in (EstadoPieza.BORRADOR, EstadoPieza.EN_MODERACION):
            raise TransicionPiezaInvalida("Solo se aprueba una pieza en borrador o en moderación.")
        self._estado = EstadoPieza.APROBADA
        self.record_event(PiezaAprobada(id_pieza=str(self.id), id_comercio=self.id_comercio))

    def rechazar(self, motivo: str) -> None:
        if self._estado not in (EstadoPieza.BORRADOR, EstadoPieza.EN_MODERACION):
            raise TransicionPiezaInvalida("Solo se rechaza una pieza en borrador o en moderación.")
        self._estado = EstadoPieza.RECHAZADA
        self.record_event(
            PiezaRechazada(id_pieza=str(self.id), id_comercio=self.id_comercio, motivo=motivo)
        )
