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
        self,
        *,
        al_dia: bool,
        excepcion_black_vigente: bool,
        hereda_black: bool = False,
        motivo: str,
    ) -> HistorialNivel | None:
        """Recalcula nivel y origen. Devuelve el registro de histórico si cambió el nivel, o None.

        §10.4: el mérito propio (al día o excepción) manda; si no lo hay pero el grupo hereda
        Black, el nivel es BLACK con origen HEREDADO_GRUPO. Un miembro Black por mérito propio no
        se pisa cuando cae el titular (su `al_dia` sigue dándole PROPIO).
        """
        if calcular_nivel(al_dia=al_dia, excepcion_black_vigente=excepcion_black_vigente) is (
            Nivel.BLACK
        ):
            nuevo, origen = Nivel.BLACK, NivelOrigen.PROPIO
        elif hereda_black:
            nuevo, origen = Nivel.BLACK, NivelOrigen.HEREDADO_GRUPO
        else:
            nuevo, origen = Nivel.PLATINO, NivelOrigen.PROPIO
        self.fecha_ultimo_calculo = datetime.now(UTC)
        cambio_nivel = nuevo != self._nivel
        anterior = self._nivel
        self._nivel = nuevo
        self.nivel_origen = (
            origen  # se persiste aunque no cambie el nivel (p. ej. PROPIO->HEREDADO)
        )
        if not cambio_nivel:
            return None
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
