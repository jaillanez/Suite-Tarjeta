"""Creación de la aplicación FastAPI (walking skeleton).

Sin lógica de negocio: solo la línea fina que atraviesa api → infraestructura → base
para demostrar que la arquitectura funciona de punta a punta.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from tarjeta.config import Settings, get_settings
from tarjeta.modules.identidad.api.routers import router as identidad_router
from tarjeta.shared.api.dependencies import SessionDep
from tarjeta.shared.api.errors import register_error_handlers
from tarjeta.shared.infrastructure.logging import configure_logging


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
