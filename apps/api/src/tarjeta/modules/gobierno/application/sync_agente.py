"""Sincronización del agente municipal con identidad (§06.0.B).

`identidad` es dueña del hecho "esta persona tiene perfil municipal"; `gobierno` es dueño
del rol y sus permisos. Al revocarse el perfil en identidad (evento), acá se desactiva al
agente para que pierda el acceso sin intervención manual.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.gobierno.infrastructure.repositories import SqlAlchemyAgenteRepository
from tarjeta.shared.domain.types import EntityId


async def desactivar_agente(payload: dict[str, Any], session: AsyncSession) -> None:
    id_persona = EntityId.from_str(str(payload["id_persona"]))
    await SqlAlchemyAgenteRepository(session).desactivar(id_persona)
