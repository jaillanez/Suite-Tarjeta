"""Integración: /health/db contra un PostgreSQL 18.6 real (testcontainers).

Verifica que la línea api → sesión async → base funcione y que el servidor sea 18
(uuidv7() es nativo desde PG 18).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest

_IMAGE = "postgres:18.6"

# Ryuk (el reaper de testcontainers) también requiere bajar su imagen; se desactiva
# para que el test dependa solo de la imagen de postgres.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

# Se saltea limpiamente si Docker no está o la imagen no está disponible localmente.
# Para habilitarlo, pre-descargar una vez:  docker pull postgres:18.6
docker = pytest.importorskip("docker")
try:  # pragma: no cover - control de entorno
    _client = docker.from_env()
    _client.ping()
    _client.images.get(_IMAGE)
except Exception:  # noqa: BLE001
    pytest.skip(
        f"Docker o imagen {_IMAGE} no disponible localmente (pre-pull: docker pull {_IMAGE})",
        allow_module_level=True,
    )

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from testcontainers.postgres import PostgresContainer  # noqa: E402

from tarjeta.main import create_app  # noqa: E402
from tarjeta.shared.infrastructure.database import session_scope  # noqa: E402


@pytest.fixture(scope="module")
def pg_url() -> AsyncIterator[str]:
    with PostgresContainer(_IMAGE, driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture
async def client(pg_url: str) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(pg_url)
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
    # uuidv7() devuelve un UUID válido
    uuid.UUID(body["uuid"])
    # el servidor es PostgreSQL 18
    assert "PostgreSQL 18" in body["server_version"]
