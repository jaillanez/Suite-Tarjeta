"""Gating de comercio habilitado (composition root, §12.1).

`promociones` no importa `comercios` (independencia de módulos): el filtro por estado del comercio
se aplica acá, en el composition root, sobre las promociones que van a ver o usar los ciudadanos.
Además de este filtro en lectura, la publicación exige comercio aprobado (guarda en el portal), así
que el único caso que este filtro atrapa es el de un comercio aprobado que luego se suspende.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.comercios.domain.comercio import ESTADOS_HABILITADOS
from tarjeta.modules.comercios.infrastructure.repositories import SqlAlchemyComercioRepository
from tarjeta.shared.domain.types import EntityId


class _ConComercio(Protocol):
    @property
    def id_comercio(self) -> EntityId: ...


async def comercios_habilitados(session: AsyncSession, ids: set[str]) -> set[str]:
    """Subconjunto de `ids` cuyos comercios están APROBADOS/ACTIVOS (§12.1)."""
    repo = SqlAlchemyComercioRepository(session)
    habilitados: set[str] = set()
    for cid in ids:
        comercio = await repo.obtener(EntityId.from_str(cid))
        if comercio is not None and comercio.estado in ESTADOS_HABILITADOS:
            habilitados.add(cid)
    return habilitados


async def filtrar_promos_habilitadas[P: _ConComercio](
    session: AsyncSession, promos: Sequence[P]
) -> list[P]:
    """Deja solo las promociones de comercios habilitados (no aprobados / suspendidos afuera)."""
    ids = {str(p.id_comercio) for p in promos}
    ok = await comercios_habilitados(session, ids)
    return [p for p in promos if str(p.id_comercio) in ok]
