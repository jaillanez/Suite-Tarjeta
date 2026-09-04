"""Handlers de eventos de ciudadania (los invoca el dispatcher; NO hacen commit)."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.ciudadania.domain.perfil_ciudadano import PerfilCiudadano
from tarjeta.modules.ciudadania.domain.ports import (
    ExcepcionRepository,
    HistorialNivelRepository,
    Outbox,
    PerfilCiudadanoRepository,
)
from tarjeta.shared.domain.types import EntityId


async def crear_perfil_al_verificar(
    *, perfiles: PerfilCiudadanoRepository, outbox: Outbox, id_persona: EntityId
) -> None:
    """Consume IdentidadVerificada: crea el PerfilCiudadano y emite la tarjeta."""
    if await perfiles.obtener(id_persona) is not None:
        return
    perfil = PerfilCiudadano.crear(id_persona)
    await perfiles.agregar(perfil)
    await outbox.escribir(perfil.pull_events())


async def recalcular_nivel(
    *,
    perfiles: PerfilCiudadanoRepository,
    historial: HistorialNivelRepository,
    excepciones: ExcepcionRepository,
    outbox: Outbox,
    id_persona: EntityId,
    al_dia: bool,
    motivo: str,
    hereda_black: bool = False,
) -> None:
    """Recalcula el nivel del perfil. `hereda_black` lo aporta el composition root según el
    grupo familiar (§10.4); por defecto False conserva el comportamiento sin grupo."""
    perfil = await perfiles.obtener(id_persona)
    if perfil is None:
        return
    hay_exc = await excepciones.hay_black_vigente(id_persona, datetime.now(UTC))
    hist = perfil.recalcular(
        al_dia=al_dia, excepcion_black_vigente=hay_exc, hereda_black=hereda_black, motivo=motivo
    )
    await perfiles.guardar(perfil)
    if hist is not None:
        await historial.agregar(hist)
    await outbox.escribir(perfil.pull_events())
