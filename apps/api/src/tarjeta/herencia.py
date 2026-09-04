"""Herencia de nivel del grupo familiar (composition root, §10.4).

No es un módulo de dominio: cablea `grupo` + `ciudadania` + `padron` para recalcular el nivel de
una persona. La herencia se recalcula POR EVENTO (no en cada lectura): estos helpers los usan los
handlers del dispatcher y el portal. Ninguno confirma la transacción (el dueño de la unidad de
trabajo —dispatcher o portal— confirma).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.ciudadania.application import handlers as ciudadania
from tarjeta.modules.ciudadania.domain.nivel import Nivel, NivelOrigen
from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyExcepcionRepository,
    SqlAlchemyHistorialNivelRepository,
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.grupo.infrastructure.repositories import SqlAlchemyGrupoRepository
from tarjeta.modules.padron.infrastructure.repositories import SqlAlchemyEstadoPadronRepository
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox


def _cipher(settings: Settings) -> FieldCipher:
    return FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )


async def _al_dia(session: AsyncSession, settings: Settings, id_persona: str) -> bool:
    estado = await SqlAlchemyEstadoPadronRepository(session, cipher=_cipher(settings)).obtener(
        EntityId.from_str(id_persona)
    )
    return bool(estado and estado.al_dia)


async def hereda_black(session: AsyncSession, id_persona: str) -> bool:
    """La persona es miembro (no titular) de un grupo activo cuyo titular es hoy BLACK (§10.4)."""
    grupos = SqlAlchemyGrupoRepository(session)
    miembro = await grupos.miembro_de(id_persona)
    if miembro is None:
        return False
    grupo = await grupos.obtener(miembro.id_grupo)
    if grupo is None or not grupo.activo or grupo.id_titular == id_persona:
        return False
    perfil = await SqlAlchemyPerfilCiudadanoRepository(session).obtener(
        EntityId.from_str(grupo.id_titular)
    )
    return perfil is not None and perfil.nivel is Nivel.BLACK


async def es_black_propio_al_dia(
    session: AsyncSession, settings: Settings, id_persona: str
) -> bool:
    """§10.1: puede crear grupo quien es Black por mérito propio y está al día."""
    perfil = await SqlAlchemyPerfilCiudadanoRepository(session).obtener(
        EntityId.from_str(id_persona)
    )
    if (
        perfil is None
        or perfil.nivel is not Nivel.BLACK
        or perfil.nivel_origen is not (NivelOrigen.PROPIO)
    ):
        return False
    return await _al_dia(session, settings, id_persona)


async def recalcular_persona(
    session: AsyncSession,
    settings: Settings,
    id_persona: str,
    *,
    motivo: str,
    al_dia: bool | None = None,
) -> None:
    """Recalcula el nivel de una persona considerando la herencia del grupo. No confirma."""
    dia = al_dia if al_dia is not None else await _al_dia(session, settings, id_persona)
    hb = await hereda_black(session, id_persona)
    await ciudadania.recalcular_nivel(
        perfiles=SqlAlchemyPerfilCiudadanoRepository(session),
        historial=SqlAlchemyHistorialNivelRepository(session),
        excepciones=SqlAlchemyExcepcionRepository(session),
        outbox=SqlAlchemyOutbox(session),
        id_persona=EntityId.from_str(id_persona),
        al_dia=dia,
        hereda_black=hb,
        motivo=motivo,
    )


async def recalcular_miembros(
    session: AsyncSession, settings: Settings, id_grupo: str, *, motivo: str
) -> None:
    """Recalcula el nivel de todos los miembros no titulares del grupo (§10.4)."""
    grupos = SqlAlchemyGrupoRepository(session)
    grupo = await grupos.obtener(EntityId.from_str(id_grupo))
    if grupo is None:
        return
    for miembro in await grupos.miembros_activos(grupo.id):
        if miembro.id_persona == grupo.id_titular:
            continue
        await recalcular_persona(session, settings, miembro.id_persona, motivo=motivo)
