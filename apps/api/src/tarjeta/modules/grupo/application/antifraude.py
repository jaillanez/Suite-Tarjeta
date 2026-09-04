"""Señales antifraude del grupo: SOLO observan, nunca bloquean un alta (§10.7).

En este paso la señal autocontenida es la **formación acelerada** (muchos miembros en pocas horas).
Otras señales (huella de dispositivo compartida, inactividad salvo en un comercio, fechas de
nacimiento incompatibles) se agregan como reglas nuevas sin cambiar el flujo de alta.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tarjeta.modules.grupo.domain.events import AlertaAntifraudeGrupo
from tarjeta.shared.domain.types import EntityId

from .deps import GrupoPuertos

FORMACION_UMBRAL = 6  # miembros
FORMACION_VENTANA = timedelta(hours=6)


class EvaluarAntifraude:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def al_agregar_miembro(self, id_grupo: EntityId) -> None:
        """Observa; genera caso si corresponde. No lanza ni frena nada."""
        miembros = await self.p.grupos.miembros_activos(id_grupo)
        ahora = datetime.now(UTC)
        recientes = [m for m in miembros if ahora - m.fecha_alta <= FORMACION_VENTANA]
        if len(recientes) >= FORMACION_UMBRAL:
            detalle = f"{len(recientes)} miembros en menos de {FORMACION_VENTANA}"
            await self.p.alertas.registrar(
                id_grupo=str(id_grupo), tipo="formacion_acelerada", detalle=detalle
            )
            await self.p.outbox.escribir(
                [
                    AlertaAntifraudeGrupo(
                        id_grupo=str(id_grupo), tipo="formacion_acelerada", detalle=detalle
                    )
                ]
            )
