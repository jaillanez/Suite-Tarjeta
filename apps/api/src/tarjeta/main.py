"""Creación de la aplicación FastAPI."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from tarjeta.config import Settings, get_settings
from tarjeta.modules.ciudadania.api.routers import router as ciudadania_router
from tarjeta.modules.comercios.api.routers import router as comercios_router
from tarjeta.modules.gobierno.api.routers import router as gobierno_router
from tarjeta.modules.identidad.api.routers import router as identidad_router
from tarjeta.modules.padron.api.routers import router as padron_router
from tarjeta.orquestacion import build_dispatcher
from tarjeta.portal_canje import router as canje_router
from tarjeta.portal_comercio import router as portal_comercio_router
from tarjeta.portal_contenido import router as contenido_router
from tarjeta.portal_grupo import router as grupo_router
from tarjeta.portal_municipal import router as portal_router
from tarjeta.portal_promociones import router as promociones_router
from tarjeta.portal_puntos import router as puntos_router
from tarjeta.shared.api.dependencies import SessionDep
from tarjeta.shared.api.errors import register_error_handlers
from tarjeta.shared.infrastructure.arranque import validar_arranque
from tarjeta.shared.infrastructure.database import get_sessionmaker
from tarjeta.shared.infrastructure.logging import configure_logging
from tarjeta.shared.infrastructure.outbox import run_worker

_log = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    # §12.2-D: en prod, negarse a arrancar con simulaciones críticas o config insegura.
    validar_arranque(cfg)
    configure_logging(cfg.debug)
    dispatcher = build_dispatcher(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Worker de segundo plano: drena el outbox aunque no haya tráfico HTTP.
        stop = asyncio.Event()
        tarea = asyncio.create_task(
            run_worker(
                get_sessionmaker(), dispatcher, intervalo_seg=cfg.outbox_intervalo_seg, stop=stop
            )
        )
        try:
            yield
        finally:
            stop.set()
            await tarea

    expose_docs = cfg.environment != "prod"
    app = FastAPI(
        title=cfg.app_name,
        version="0.1.0",
        docs_url="/docs" if expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(identidad_router)
    app.include_router(padron_router)
    app.include_router(ciudadania_router)
    app.include_router(gobierno_router)
    app.include_router(comercios_router)
    app.include_router(portal_router)
    app.include_router(portal_comercio_router)
    app.include_router(promociones_router)
    app.include_router(canje_router)
    app.include_router(puntos_router)
    app.include_router(grupo_router)
    app.include_router(contenido_router)

    @app.middleware("http")
    async def _drenar_eventos(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        # Entrega los eventos de dominio pendientes (comunicación entre módulos).
        try:
            async with get_sessionmaker()() as session:
                await dispatcher.drain(session)
        except Exception:  # noqa: BLE001 - el drenado nunca debe romper la respuesta
            _log.exception("Fallo drenando el outbox de eventos")
        return response

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db", tags=["health"])
    async def health_db(session: SessionDep) -> dict[str, str]:
        result = await session.execute(text("SELECT uuidv7() AS uuid, version() AS server_version"))
        row = result.mappings().one()
        return {
            "uuid": str(row["uuid"]),
            "server_version": str(row["server_version"]),
        }

    return app


app = create_app()
