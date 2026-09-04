"""Nivel de confianza del comercio para moderación (§4.4, §07.5).

NUEVO: revisión humana previa. ESTABLECIDO: publicación automática (revisión solo si hay
señal). VERIFICADO: publicación inmediata, auditoría posterior por muestreo. La promoción de
nivel es automática por buen historial, con los umbrales en parametría (los inyecta el
composition root; el dominio recibe enteros).
"""

from __future__ import annotations

from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .events import NivelConfianzaCambiado


class NivelConfianza(StrEnum):
    NUEVO = "NUEVO"
    ESTABLECIDO = "ESTABLECIDO"
    VERIFICADO = "VERIFICADO"


def requiere_revision_previa(nivel: NivelConfianza) -> bool:
    return nivel is NivelConfianza.NUEVO


class PerfilConfianza(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        nivel: NivelConfianza = NivelConfianza.NUEVO,
        promos_aprobadas: int = 0,
    ) -> None:
        super().__init__(id)  # id == id_comercio
        self.nivel = nivel
        self.promos_aprobadas = promos_aprobadas

    @property
    def id_comercio(self) -> EntityId:
        return self.id

    def registrar_aprobacion(self, *, umbral_establecido: int, umbral_verificado: int) -> None:
        """Suma una promoción aprobada y promueve de nivel si corresponde."""
        self.promos_aprobadas += 1
        nuevo = self._nivel_por_historial(umbral_establecido, umbral_verificado)
        if nuevo is not self.nivel:
            anterior = self.nivel
            self.nivel = nuevo
            self.record_event(
                NivelConfianzaCambiado(
                    id_comercio=str(self.id),
                    nivel_anterior=anterior.value,
                    nivel_nuevo=nuevo.value,
                )
            )

    def _nivel_por_historial(
        self, umbral_establecido: int, umbral_verificado: int
    ) -> NivelConfianza:
        if self.promos_aprobadas >= umbral_verificado:
            return NivelConfianza.VERIFICADO
        if self.promos_aprobadas >= umbral_establecido:
            return NivelConfianza.ESTABLECIDO
        return NivelConfianza.NUEVO
