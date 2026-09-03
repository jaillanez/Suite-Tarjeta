"""Integración: /health/db contra un PostgreSQL 18 real.

En CI usa el *service container* (via `TARJETA_INTEGRATION_DATABASE_URL`). En local,
si hay una base alcanzable la corre; si no, se saltea con un mensaje claro.
Verifica la línea api → sesión async → base y que `uuidv7()` (nativo en PG 18) funcione.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tarjeta.config import get_settings
from tarjeta.main import create_app
from tarjeta.shared.infrastructure.database import session_scope

pytestmark = pytest.mark.integration


def _integration_db_url() -> str | None:
    explicit = os.getenv("TARJETA_INTEGRATION_DATABASE_URL")
    if explicit:
        return explicit
    try:
        return str(get_settings().database_url)
    except Exception:  # noqa: BLE001 - config incompleta en local
        return None


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    url = _integration_db_url()
    if not url:
        pytest.skip("Sin URL de base para integración (TARJETA_INTEGRATION_DATABASE_URL)")

    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - base no disponible en local
        await engine.dispose()
        pytest.skip(f"Base no disponible para integración: {exc}")

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_session() -> AsyncIterator[object]:
        async with sessionmaker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[session_scope] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_db(client: AsyncClient) -> None:
    resp = await client.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    uuid.UUID(body["uuid"])  # uuidv7() devuelve un UUID válido
    assert "PostgreSQL 18" in body["server_version"]
