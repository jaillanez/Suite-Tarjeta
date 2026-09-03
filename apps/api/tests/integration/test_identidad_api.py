"""Integración de la API de identidad (PostgreSQL + Redis reales)."""

from __future__ import annotations

import os
import random
from collections.abc import AsyncIterator

import pyotp
import pytest

pytestmark = pytest.mark.integration

docker = None  # este test no usa docker; requiere DB + Redis alcanzables

from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402
from tarjeta.shared.domain.types import cuil_check_digit  # noqa: E402


def _ident() -> tuple[str, str, str]:
    """DNI, CUIL válido y celular únicos por test."""
    while True:
        dni = str(random.randint(10_000_000, 39_999_999))
        first10 = "20" + dni
        dv = cuil_check_digit(first10)
        if dv != 10:
            break
    cuil = first10 + str(dv)
    celular = f"264{random.randint(1000000, 9999999)}"
    return dni, cuil, celular


def _consentimientos(opcionales: bool = True) -> list[dict[str, object]]:
    return [
        {"tipo": "TRATAMIENTO_DATOS", "otorgado": True},
        {"tipo": "COMUNICACIONES_COMERCIALES", "otorgado": opcionales},
        {"tipo": "GEOLOCALIZACION", "otorgado": opcionales},
        {"tipo": "ESTADISTICA_ANONIMA", "otorgado": opcionales},
    ]


class _CapturingOtp:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    async def enviar(self, celular: str, codigo: str) -> None:
        self._store[celular] = codigo


@pytest.fixture
async def ctx() -> AsyncIterator[tuple[AsyncClient, dict[str, str]]]:
    settings = get_settings()
    db_url = os.getenv("TARJETA_INTEGRATION_DATABASE_URL") or str(settings.database_url)
    engine = create_async_engine(db_url)
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
    # Estado limpio por test: evita que el rate limiter (misma IP) se acumule.
    await redis.flushdb()

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    capturado: dict[str, str] = {}

    from tarjeta.modules.identidad.api.deps import get_puertos
    from tarjeta.modules.identidad.infrastructure.composition import construir_puertos

    async def _override() -> AsyncIterator[object]:
        async with sessionmaker() as session:
            puertos = construir_puertos(session, settings, redis)
            puertos.envio_otp = _CapturingOtp(capturado)
            yield puertos

    app = create_app()
    app.dependency_overrides[get_puertos] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, capturado
    await engine.dispose()
    await redis.aclose()


async def _registrar_y_loguear(
    client: AsyncClient, capturado: dict[str, str], *, opcionales: bool = True
) -> tuple[str, dict[str, str]]:
    dni, cuil, celular = _ident()
    password = "contrasena-larga-123"
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": dni,
            "cuil": cuil,
            "apellido": "Gómez",
            "nombre": "Ana",
            "celular": celular,
            "password": password,
            "consentimientos": _consentimientos(opcionales),
        },
    )
    assert r.status_code == 201, r.text
    codigo = capturado[celular]
    r = await client.post(
        "/api/v1/auth/verificar-celular", json={"celular": celular, "codigo": codigo}
    )
    assert r.status_code == 200, r.text
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mfa_requerido"] is False
    return dni, body["tokens"]


async def test_flujo_registro_login_me(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, capturado = ctx
    dni, tokens = await _registrar_y_loguear(client, capturado)
    r = await client.get(
        "/api/v1/personas/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert r.status_code == 200
    assert r.json()["dni"] == dni
    # Perfiles: solo ciudadano
    r = await client.get(
        "/api/v1/auth/perfiles", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert [p["tipo"] for p in r.json()] == ["CIUDADANO"]


async def test_login_no_filtra_usuario_inexistente(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, _ = ctx
    r = await client.post("/api/v1/auth/login", json={"dni": "99999999", "password": "x"})
    assert r.status_code == 401


async def test_refresh_rotacion_y_reuso(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, capturado = ctx
    _, tokens = await _registrar_y_loguear(client, capturado)
    refresh1 = tokens["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 200
    # Reusar el refresh viejo revoca la familia -> 401.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 401


async def test_perfil_no_asignado_devuelve_403(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, capturado = ctx
    _, tokens = await _registrar_y_loguear(client, capturado)
    r = await client.post(
        "/api/v1/auth/perfiles/MUNICIPAL/activar",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 403


async def test_rechazar_opcionales_permite_usar(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, capturado = ctx
    _, tokens = await _registrar_y_loguear(client, capturado, opcionales=False)
    r = await client.get(
        "/api/v1/personas/me/consentimientos",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    estado = r.json()
    assert estado["TRATAMIENTO_DATOS"] is True
    assert estado["GEOLOCALIZACION"] is False


async def test_falta_consentimiento_obligatorio(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, _ = ctx
    dni, cuil, celular = _ident()
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": dni,
            "cuil": cuil,
            "apellido": "Gómez",
            "nombre": "Ana",
            "celular": celular,
            "password": "contrasena-larga-123",
            "consentimientos": [{"tipo": "TRATAMIENTO_DATOS", "otorgado": False}],
        },
    )
    assert r.status_code == 409


async def test_mfa_flujo(ctx: tuple[AsyncClient, dict[str, str]]) -> None:
    client, capturado = ctx
    dni, tokens = await _registrar_y_loguear(client, capturado)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.post("/api/v1/personas/me/mfa/activar", headers=headers)
    assert r.status_code == 200
    secreto = r.json()["secreto"]
    # Nuevo login: ahora exige MFA.
    r = await client.post(
        "/api/v1/auth/login", json={"dni": dni, "password": "contrasena-larga-123"}
    )
    body = r.json()
    assert body["mfa_requerido"] is True
    codigo = pyotp.TOTP(secreto).now()
    r = await client.post(
        "/api/v1/auth/mfa/verificar", json={"mfa_token": body["mfa_token"], "codigo": codigo}
    )
    assert r.status_code == 200
    assert r.json()["tokens"]["access_token"]


async def test_dispositivos_registro_listado_revoke(
    ctx: tuple[AsyncClient, dict[str, str]],
) -> None:
    client, capturado = ctx
    _, tokens = await _registrar_y_loguear(client, capturado)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = await client.post(
        "/api/v1/personas/me/dispositivos",
        headers=headers,
        json={"nombre_declarado": "Mi teléfono", "plataforma": "android", "huella": "abc123"},
    )
    assert r.status_code == 200
    id_disp = r.json()["id"]
    r = await client.get("/api/v1/personas/me/dispositivos", headers=headers)
    assert any(d["id"] == id_disp for d in r.json())
    r = await client.delete(f"/api/v1/personas/me/dispositivos/{id_disp}", headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/v1/personas/me/dispositivos", headers=headers)
    assert all(d["estado"] == "REVOCADO" for d in r.json() if d["id"] == id_disp)
