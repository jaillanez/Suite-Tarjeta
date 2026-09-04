"""Agregado Promocion (§1.6, §07.2) con máquina de estados y reglas de dominio."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import (
    PromocionActivaInmutable,
    SegmentoNoAplica,
    TopeInvalido,
    TransicionPromocionInvalida,
)
from .events import EstadoPromocionCambiado, PromocionCreada
from .mecanica import Mecanica, Segmento, beneficio_relativo
from .vigencia import Vigencia


class EstadoPromocion(StrEnum):
    BORRADOR = "BORRADOR"
    EN_REVISION = "EN_REVISION"
    APROBADA = "APROBADA"
    ACTIVA = "ACTIVA"
    PAUSADA = "PAUSADA"
    RECHAZADA = "RECHAZADA"
    VENCIDA = "VENCIDA"
    AGOTADA = "AGOTADA"


_TRANSICIONES: dict[EstadoPromocion, set[EstadoPromocion]] = {
    EstadoPromocion.BORRADOR: {EstadoPromocion.EN_REVISION, EstadoPromocion.ACTIVA},
    EstadoPromocion.EN_REVISION: {EstadoPromocion.APROBADA, EstadoPromocion.RECHAZADA},
    EstadoPromocion.APROBADA: {EstadoPromocion.ACTIVA},
    EstadoPromocion.ACTIVA: {
        EstadoPromocion.PAUSADA,
        EstadoPromocion.VENCIDA,
        EstadoPromocion.AGOTADA,
    },
    EstadoPromocion.PAUSADA: {EstadoPromocion.ACTIVA, EstadoPromocion.VENCIDA},
    EstadoPromocion.RECHAZADA: set(),
    EstadoPromocion.VENCIDA: set(),
    EstadoPromocion.AGOTADA: set(),
}


class Promocion(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_comercio: EntityId,
        titulo: str,
        descripcion: str,
        mecanica: Mecanica,
        segmento: Segmento,
        valor_platino: int | None,
        valor_black: int,
        vigencia: Vigencia,
        sucursales: list[EntityId],
        acumulable: bool = False,
        destacada_municipal: bool = False,
        tope_total: int | None = None,
        tope_por_usuario: int | None = None,
        tope_por_dia: int | None = None,
        usos_totales: int = 0,
        monto_minimo: int = 0,
        imagen_url: str = "",
        estado: EstadoPromocion = EstadoPromocion.BORRADOR,
        creada_en: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.id_comercio = id_comercio
        self.titulo = titulo
        self.descripcion = descripcion
        self.mecanica = mecanica
        self.segmento = segmento
        self.valor_platino = valor_platino
        self.valor_black = valor_black
        self.vigencia = vigencia
        self.sucursales = sucursales
        self.acumulable = acumulable
        self.destacada_municipal = destacada_municipal
        self.tope_total = tope_total
        self.tope_por_usuario = tope_por_usuario
        self.tope_por_dia = tope_por_dia
        self.usos_totales = usos_totales
        self.monto_minimo = monto_minimo
        self.imagen_url = imagen_url
        self._estado = estado
        self.creada_en = creada_en or datetime.now(UTC)

    @classmethod
    def crear(
        cls,
        *,
        id_comercio: EntityId,
        titulo: str,
        descripcion: str,
        mecanica: Mecanica,
        segmento: Segmento,
        valor_platino: int | None,
        valor_black: int,
        vigencia: Vigencia,
        sucursales: list[EntityId],
        acumulable: bool = False,
        tope_total: int | None = None,
        tope_por_usuario: int | None = None,
        tope_por_dia: int | None = None,
        monto_minimo: int = 0,
        imagen_url: str = "",
    ) -> Promocion:
        if segmento is Segmento.SOLO_BLACK and valor_platino is not None:
            raise SegmentoNoAplica("Una promoción exclusiva Black no lleva valor Platino.")
        for tope in (tope_total, tope_por_usuario, tope_por_dia):
            if tope is not None and tope <= 0:
                raise TopeInvalido("Los topes deben ser positivos.")
        promo = cls(
            id=EntityId.new(),
            id_comercio=id_comercio,
            titulo=titulo,
            descripcion=descripcion,
            mecanica=mecanica,
            segmento=segmento,
            valor_platino=valor_platino,
            valor_black=valor_black,
            vigencia=vigencia,
            sucursales=sucursales,
            acumulable=acumulable,
            tope_total=tope_total,
            tope_por_usuario=tope_por_usuario,
            tope_por_dia=tope_por_dia,
            monto_minimo=monto_minimo,
            imagen_url=imagen_url,
        )
        promo.record_event(
            PromocionCreada(id_promocion=str(promo.id), id_comercio=str(id_comercio))
        )
        return promo

    @property
    def estado(self) -> EstadoPromocion:
        return self._estado

    def _cambiar_estado(self, destino: EstadoPromocion, motivo: str) -> None:
        if destino not in _TRANSICIONES[self._estado]:
            raise TransicionPromocionInvalida(
                f"No se puede pasar de {self._estado.value} a {destino.value}."
            )
        anterior = self._estado
        self._estado = destino
        self.record_event(
            EstadoPromocionCambiado(
                id_promocion=str(self.id),
                id_comercio=str(self.id_comercio),
                estado_anterior=anterior.value,
                estado_nuevo=destino.value,
                motivo=motivo,
            )
        )

    def enviar_a_revision(self) -> None:
        self._cambiar_estado(EstadoPromocion.EN_REVISION, "enviada a revisión")

    def aprobar(self) -> None:
        self._cambiar_estado(EstadoPromocion.APROBADA, "aprobada")

    def rechazar(self, motivo: str) -> None:
        self._cambiar_estado(EstadoPromocion.RECHAZADA, motivo)

    def activar(self) -> None:
        # Publicación directa (comercio de confianza) o tras aprobación.
        if self._estado is EstadoPromocion.BORRADOR:
            self._cambiar_estado(EstadoPromocion.ACTIVA, "publicación directa")
        else:
            self._cambiar_estado(EstadoPromocion.ACTIVA, "activada")

    def pausar(self) -> None:
        self._cambiar_estado(EstadoPromocion.PAUSADA, "pausada")

    def reanudar(self) -> None:
        self._cambiar_estado(EstadoPromocion.ACTIVA, "reanudada")

    def vencer(self) -> None:
        self._cambiar_estado(EstadoPromocion.VENCIDA, "vencida")

    def marcar_agotada(self) -> None:
        self._cambiar_estado(EstadoPromocion.AGOTADA, "tope alcanzado")

    # --- edición (§07.2: condiciones económicas inmutables en ACTIVA) --------
    def editar_condiciones_economicas(
        self,
        *,
        mecanica: Mecanica,
        valor_platino: int | None,
        valor_black: int,
        tope_total: int | None,
    ) -> None:
        if self._estado is EstadoPromocion.ACTIVA:
            raise PromocionActivaInmutable(
                "Una promoción activa no puede cambiar sus condiciones económicas. "
                "Pausala y creá una nueva."
            )
        if tope_total is not None and tope_total < self.usos_totales:
            raise TopeInvalido("El tope no puede bajar por debajo de los usos ya consumidos.")
        self.mecanica = mecanica
        self.valor_platino = valor_platino
        self.valor_black = valor_black
        self.tope_total = tope_total

    def editar_presentacion(self, *, titulo: str, descripcion: str, imagen_url: str) -> None:
        # Título/descuento/imagen: se pueden ajustar aun estando activa (no cambia lo económico).
        self.titulo = titulo
        self.descripcion = descripcion
        self.imagen_url = imagen_url

    # --- consultas de dominio -------------------------------------------------
    def aplica_a_nivel(self, nivel: str) -> bool:
        if self.segmento is Segmento.SOLO_BLACK:
            return nivel == "BLACK"
        return nivel in ("PLATINO", "BLACK")

    def valor_para(self, nivel: str) -> int:
        if nivel == "BLACK":
            return self.valor_black
        return self.valor_platino if self.valor_platino is not None else 0

    def beneficio_para(self, nivel: str) -> float:
        return beneficio_relativo(self.mecanica, self.valor_para(nivel))
