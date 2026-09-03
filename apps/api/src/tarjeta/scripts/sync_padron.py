"""Batch nocturno de sincronización con el padrón (§7.2).

Reconsulta el veredicto de todas las personas con estado conocido, con concurrencia
acotada y tolerante a fallas individuales, y recalcula los niveles por eventos.

Ejecutable a mano:  uv run python -m tarjeta.scripts.sync_padron
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from tarjeta.config import get_settings
from tarjeta.modules.padron.application import consultar as padron
from tarjeta.modules.padron.infrastructure.composition import construir_cliente
from tarjeta.modules.padron.infrastructure.models import EstadoPadronModel
from tarjeta.modules.padron.infrastructure.repositories import SqlAlchemyEstadoPadronRepository
from tarjeta.orquestacion import build_dispatcher
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.database import get_sessionmaker
from tarjeta.shared.infrastructure.logging import configure_logging
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

_log = logging.getLogger("batch.padron")
_CONCURRENCIA = 5


async def ejecutar() -> int:
    settings = get_settings()
    configure_logging(settings.debug)
    cipher = FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )
    cliente = construir_cliente(settings)
    dispatcher = build_dispatcher(settings)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        ids = list((await session.execute(select(EstadoPadronModel.id_persona))).scalars())

    sem = asyncio.Semaphore(_CONCURRENCIA)
    procesados = 0

    async def procesar(id_persona_val: object) -> None:
        nonlocal procesados
        async with sem:
            try:
                async with sessionmaker() as s:
                    await padron.reconsultar(
                        repo=SqlAlchemyEstadoPadronRepository(s, cipher=cipher),
                        cliente=cliente,
                        outbox=SqlAlchemyOutbox(s),
                        id_persona=EntityId(id_persona_val),  # type: ignore[arg-type]
                        origen=padron.BATCH,
                    )
                    await s.commit()
                procesados += 1
            except Exception:  # noqa: BLE001 - una falla individual no corta el lote
                _log.exception("Fallo sincronizando una persona en el batch")

    await asyncio.gather(*(procesar(i) for i in ids))

    # Recalcular niveles a partir de los eventos emitidos.
    async with sessionmaker() as s:
        await dispatcher.drain(s)

    _log.info("Batch de padrón: %s personas procesadas", procesados)
    return procesados


def main() -> None:
    asyncio.run(ejecutar())


if __name__ == "__main__":
    main()
