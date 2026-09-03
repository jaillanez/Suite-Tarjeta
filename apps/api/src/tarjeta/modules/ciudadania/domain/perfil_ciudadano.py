"""Agregado PerfilCiudadano (§1.2). El nivel no tiene setter público."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .events import NivelCambiado, TarjetaEmitida
from .historial_nivel import HistorialNivel
from .nivel import REGLA_VIGENTE, Nivel, NivelOrigen, calcular_nivel
from .tarjeta import EstadoTarjeta, generar_numero_tarjeta


class PerfilCiudadano(AggregateRoot):
    def __init__(
        self,
        *,
        id_persona: EntityId,
        nivel: Nivel,
        nivel_origen: NivelOrigen,
        numero_tarjeta: str,
        estado_tarjeta: EstadoTarjeta,
        tiene_tarjeta_fisica: bool,
        fecha_ultimo_calculo: datetime,
    ) -> None:
        super().__init__(id_persona)
        self._nivel = nivel
        self.nivel_origen = nivel_origen
        self.numero_tarjeta = numero_tarjeta
        self.estado_tarjeta = estado_tarjeta
        self.tiene_tarjeta_fisica = tiene_tarjeta_fisica
        self.fecha_ultimo_calculo = fecha_ultimo_calculo

    @property
    def id_persona(self) -> EntityId:
        return self.id

    @property
    def nivel(self) -> Nivel:
        return self._nivel

    @classmethod
    def crear(cls, id_persona: EntityId) -> PerfilCiudadano:
        """Se crea al verificarse la identidad: nivel base Platino y tarjeta emitida."""
        perfil = cls(
            id_persona=id_persona,
            nivel=Nivel.PLATINO,
            nivel_origen=NivelOrigen.PROPIO,
            numero_tarjeta=generar_numero_tarjeta(),
            estado_tarjeta=EstadoTarjeta.ACTIVA,
            tiene_tarjeta_fisica=False,
            fecha_ultimo_calculo=datetime.now(UTC),
        )
        perfil.record_event(
            TarjetaEmitida(id_persona=str(id_persona), numero_tarjeta=perfil.numero_tarjeta)
        )
        return perfil

    @classmethod
    def rehidratar(cls, **kwargs: object) -> PerfilCiudadano:
        return cls(**kwargs)  # type: ignore[arg-type]

    def recalcular(
        self, *, al_dia: bool, excepcion_black_vigente: bool, motivo: str
    ) -> HistorialNivel | None:
        """Recalcula el nivel. Devuelve el registro de histórico si cambió, o None."""
        nuevo = calcular_nivel(al_dia=al_dia, excepcion_black_vigente=excepcion_black_vigente)
        self.fecha_ultimo_calculo = datetime.now(UTC)
        if nuevo == self._nivel:
            return None
        anterior = self._nivel
        self._nivel = nuevo
        self.record_event(
            NivelCambiado(
                id_persona=str(self.id),
                nivel_anterior=str(anterior),
                nivel_nuevo=str(nuevo),
                motivo=motivo,
            )
        )
        return HistorialNivel(
            id=EntityId.new(),
            id_persona=self.id,
            nivel_anterior=str(anterior),
            nivel_nuevo=str(nuevo),
            motivo=motivo,
            detalle_regla_aplicada=REGLA_VIGENTE,
            timestamp=self.fecha_ultimo_calculo,
        )

    def bloquear_tarjeta(self) -> None:
        self.estado_tarjeta = EstadoTarjeta.BLOQUEADA

    def reemitir_tarjeta(self) -> None:
        self.numero_tarjeta = generar_numero_tarjeta()
        self.estado_tarjeta = EstadoTarjeta.ACTIVA
