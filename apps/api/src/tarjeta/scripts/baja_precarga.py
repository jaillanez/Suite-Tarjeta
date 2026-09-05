"""Baja en bloque de los comercios de precarga (§13.3).

El día que se abra al público hay que poder distinguir los comercios precargados de los que se
adhirieron de verdad, y darlos de baja de una sola vez. Esto pone en estado BAJA a todos los
comercios con la bandera `precarga` (dejan de aparecer en mapa/feed y de operar), sin tocar a los
comercios reales.

Uso:  uv run python -m tarjeta.scripts.baja_precarga
"""

from __future__ import annotations

import asyncio

from sqlalchemy import update

from tarjeta.modules.comercios.infrastructure.models import ComercioModel
from tarjeta.shared.infrastructure.database import get_sessionmaker


async def _baja() -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as s:
        res = await s.execute(
            update(ComercioModel)
            .where(ComercioModel.precarga.is_(True), ComercioModel.estado != "BAJA")
            .values(estado="BAJA")
        )
        await s.commit()
        return int(res.rowcount or 0)  # type: ignore[attr-defined]  # CursorResult


def main() -> None:
    n = asyncio.run(_baja())
    print(f"Comercios de precarga dados de baja: {n}")


if __name__ == "__main__":
    main()
