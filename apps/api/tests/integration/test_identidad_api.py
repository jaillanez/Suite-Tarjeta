"""Integración de la API de identidad (registro mínimo sin OTP)."""

from __future__ import annotations

import random
from collections.abc import AsyncIterator

import pyotp
import pytest

pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402


def _dni() -> str:
    return str(random.randint(10_000_000, 39_999_999))


def _consentimientos(opcionales: bool = True) -> list[dict[str, object]]:
    return [
        {"tipo": "TRATAMIENTO_DATOS", "otorgado": True},
        {"tipo": "COMUNICACIONES_COMERCIALES", "otorgado": opcionales},
        {"tipo": "GEOLOCALIZACION", "otorgado": opcionales},
        {"tipo": "ESTADISTICA_ANONIMA", "otorgado": opcionales},
    ]


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await redis.aclose()


PASSWORD = "contrasena-larga-123"


async def _registrar(
    client: AsyncClient, *, opcionales: bool = True, dni: str | None = None
) -> str:
    d = dni or _dni()
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": d,
            "fecha_nacimiento": "1990-05-20",
            "password": PASSWORD,
            "consentimientos": _consentimientos(opcionales),
        },
    )
    assert r.status_code == 201, r.text
    return d


async def _login(client: AsyncClient, dni: str) -> dict[str, str]:
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mfa_requerido"] is False
    return body["tokens"]


async def test_registro_login_me(client: AsyncClient) -> None:
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    r = await client.get(
        "/api/v1/personas/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dni"] == dni
    assert body["estado_identidad"] == "VERIFICADA"  # auto-verificado en esta etapa


async def test_login_no_filtra_usuario_inexistente(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/login", json={"dni": "99999999", "password": "x"})
    assert r.status_code == 401


async def test_refresh_rotacion_y_reuso(client: AsyncClient) -> None:
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    refresh1 = tokens["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 200
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 401


async def test_perfil_no_asignado_403(client: AsyncClient) -> None:
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    r = await client.post(
        "/api/v1/auth/perfiles/MUNICIPAL/activar",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 403


async def test_rechazar_opcionales_permite_usar(client: AsyncClient) -> None:
    dni = await _registrar(client, opcionales=False)
    tokens = await _login(client, dni)
    r = await client.get(
        "/api/v1/personas/me/consentimientos",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["TRATAMIENTO_DATOS"] is True
    assert r.json()["GEOLOCALIZACION"] is False


async def test_falta_consentimiento_obligatorio(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": _dni(),
            "fecha_nacimiento": "1990-05-20",
            "password": PASSWORD,
            "consentimientos": [{"tipo": "TRATAMIENTO_DATOS", "otorgado": False}],
        },
    )
    assert r.status_code == 409


async def test_mfa_flujo(client: AsyncClient) -> None:
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.post("/api/v1/personas/me/mfa/activar", headers=headers)
    assert r.status_code == 200
    secreto = r.json()["secreto"]
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": PASSWORD})
    body = r.json()
    assert body["mfa_requerido"] is True
    r = await client.post(
        "/api/v1/auth/mfa/verificar",
        json={"mfa_token": body["mfa_token"], "codigo": pyotp.TOTP(secreto).now()},
    )
    assert r.status_code == 200
    assert r.json()["tokens"]["access_token"]


async def test_dispositivos(client: AsyncClient) -> None:
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.post(
        "/api/v1/personas/me/dispositivos",
        headers=headers,
        json={"nombre_declarado": "Tel", "plataforma": "android", "huella": "abc"},
    )
    assert r.status_code == 200
    id_disp = r.json()["id"]
    r = await client.delete(f"/api/v1/personas/me/dispositivos/{id_disp}", headers=headers)
    assert r.status_code == 200
