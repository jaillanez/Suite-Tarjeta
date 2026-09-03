"""Creación de la aplicación FastAPI."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from tarjeta.config import Settings, get_settings
from tarjeta.modules.ciudadania.api.routers import router as ciudadania_router
from tarjeta.modules.identidad.api.routers import router as identidad_router
from tarjeta.modules.padron.api.routers import router as padron_router
from tarjeta.orquestacion import build_dispatcher
from tarjeta.shared.api.dependencies import SessionDep
from tarjeta.shared.api.errors import register_error_handlers
from tarjeta.shared.infrastructure.database import get_sessionmaker
from tarjeta.shared.infrastructure.logging import configure_logging

_log = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    configure_logging(cfg.debug)

    expose_docs = cfg.environment != "prod"
    app = FastAPI(
        title=cfg.app_name,
        version="0.1.0",
        docs_url="/docs" if expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_docs else None,
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

    dispatcher = build_dispatcher(cfg)

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
