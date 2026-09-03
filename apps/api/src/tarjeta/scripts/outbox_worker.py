"""Worker de segundo plano del outbox de eventos (§05.1).

Drena el outbox de forma continua e independiente del tráfico HTTP: entrega cada evento
a sus handlers en su propia transacción, con reintentos con retroceso exponencial y cola
de muertos. Corre como proceso aparte de la API (mismo cableado del dispatcher).

Ejecutable a mano:  uv run python -m tarjeta.scripts.outbox_worker
Se detiene limpio con SIGINT/SIGTERM (Ctrl-C).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from tarjeta.config import get_settings
from tarjeta.orquestacion import build_dispatcher
from tarjeta.shared.infrastructure.database import get_sessionmaker
from tarjeta.shared.infrastructure.logging import configure_logging
from tarjeta.shared.infrastructure.outbox import run_worker

_log = logging.getLogger("worker.outbox")


async def ejecutar() -> None:
    settings = get_settings()
    configure_logging(settings.debug)
    dispatcher = build_dispatcher(settings)
    sessionmaker = get_sessionmaker()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # p. ej. en Windows
            loop.add_signal_handler(sig, stop.set)

    _log.info("Worker de outbox iniciado (intervalo %ss)", settings.outbox_intervalo_seg)
    await run_worker(
        sessionmaker, dispatcher, intervalo_seg=settings.outbox_intervalo_seg, stop=stop
    )
    _log.info("Worker de outbox detenido")


def main() -> None:
    asyncio.run(ejecutar())


if __name__ == "__main__":
    main()
