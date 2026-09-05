"""Integración: identidad verificada -> perfil -> padrón -> nivel -> tarjeta."""

from __future__ import annotations

import random
from collections.abc import AsyncIterator

import pytest

pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402

PASSWORD = "contrasena-larga-123"


def _dni() -> str:
    # §13.1: sin paridad. El nivel se controla sembrando el padrón (fixture `padron`).
    return str(random.randint(10_000_000, 39_999_999))


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))
    try:
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Base no disponible: {exc}")
    redis = Redis.from_url(str(settings.redis_url))
    try:
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Redis no disponible: {exc}")
    await redis.flushdb()
    await engine.dispose()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await redis.aclose()


async def _registrar_login(client: AsyncClient, dni: str) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": dni,
            "fecha_nacimiento": "1985-03-10",
            "password": PASSWORD,
            "consentimientos": [{"tipo": "TRATAMIENTO_DATOS", "otorgado": True}],
        },
    )
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["tokens"]


async def test_al_dia_es_black(client: AsyncClient, padron) -> None:
    dni = _dni()
    padron.al_dia(dni, True)
    tokens = await _registrar_login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.get("/api/v1/ciudadania/mi-estado", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["nivel"] == "BLACK"


async def test_no_al_dia_es_platino(client: AsyncClient, padron) -> None:
    dni = _dni()
    padron.al_dia(dni, False)
    tokens = await _registrar_login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.get("/api/v1/ciudadania/mi-estado", headers=headers)
    assert r.status_code == 200
    assert r.json()["nivel"] == "PLATINO"


async def test_padron_mi_estado_y_tarjeta(client: AsyncClient, padron) -> None:
    dni = _dni()
    padron.al_dia(dni, True)
    tokens = await _registrar_login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.get("/api/v1/padron/mi-estado", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["consultado"] is True
    assert body["al_dia"] is True
    assert body["horas_desde_consulta"] is not None

    r = await client.get("/api/v1/ciudadania/mi-estado", headers=headers)
    assert len(r.json()["numero_tarjeta"]) == 16


async def test_actualizar_estado_limite_diario(client: AsyncClient, padron) -> None:
    dni = _dni()
    padron.al_dia(dni, False)
    tokens = await _registrar_login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    for _ in range(3):
        r = await client.post("/api/v1/ciudadania/actualizar-estado", headers=headers)
        assert r.status_code == 200, r.text
    r = await client.post("/api/v1/ciudadania/actualizar-estado", headers=headers)
    assert r.status_code == 409  # límite diario alcanzado
