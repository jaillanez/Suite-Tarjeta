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


async def test_registro_queda_autodeclarada(client: AsyncClient) -> None:
    # §12.2-C: el alta por la app queda AUTODECLARADA (nunca RENAPER, que está fuera de alcance).
    dni = await _registrar(client)
    tokens = await _login(client, dni)
    me = (
        await client.get(
            "/api/v1/personas/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
    ).json()
    engine = create_async_engine(str(get_settings().database_url))
    try:
        async with engine.connect() as c:
            metodo = (
                await c.execute(
                    text("SELECT metodo_verificacion FROM persona WHERE id = :id"),
                    {"id": me["id"]},
                )
            ).scalar_one()
    finally:
        await engine.dispose()
    assert metodo == "AUTODECLARADA"


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


# --- §12 P1-A: sesión web con refresh en cookie HttpOnly -----------------------

_COOKIE_HDR = {"X-Auth-Mode": "cookie"}


async def test_login_modo_cookie_no_expone_refresh_en_cuerpo(client: AsyncClient) -> None:
    dni = await _registrar(client)
    r = await client.post(
        "/api/v1/auth/login", json={"dni": dni, "password": PASSWORD}, headers=_COOKIE_HDR
    )
    assert r.status_code == 200, r.text
    tokens = r.json()["tokens"]
    assert tokens["access_token"]  # el access sí viaja (la web lo guarda en memoria)
    assert tokens["refresh_token"] == ""  # el refresh NO se expone a JS
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "tarjeta_refresh=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert client.cookies.get("tarjeta_refresh")  # quedó en el jar (HttpOnly)


async def test_refresh_modo_cookie_usa_la_cookie_y_rota(client: AsyncClient) -> None:
    dni = await _registrar(client)
    await client.post(
        "/api/v1/auth/login", json={"dni": dni, "password": PASSWORD}, headers=_COOKIE_HDR
    )
    # Cuerpo vacío: el refresh viaja en la cookie que el navegador reenvía.
    r = await client.post("/api/v1/auth/refresh", json={}, headers=_COOKIE_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"] == ""  # sigue sin exponerse en el cuerpo
    assert client.cookies.get("tarjeta_refresh")  # rotada


async def test_logout_modo_cookie_borra_la_cookie(client: AsyncClient) -> None:
    dni = await _registrar(client)
    await client.post(
        "/api/v1/auth/login", json={"dni": dni, "password": PASSWORD}, headers=_COOKIE_HDR
    )
    r = await client.post("/api/v1/auth/logout", json={}, headers=_COOKIE_HDR)
    assert r.status_code == 200
    # Tras el logout la sesión por cookie ya no sirve (revocada + cookie borrada).
    r2 = await client.post("/api/v1/auth/refresh", json={}, headers=_COOKIE_HDR)
    assert r2.status_code == 401


# --- recuperación de cuenta por email (§04.0.B) --------------------------------


async def _registrar_con_email(client: AsyncClient, email: str) -> str:
    dni = _dni()
    r = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": dni,
            "fecha_nacimiento": "1990-05-20",
            "password": PASSWORD,
            "email": email,
            "consentimientos": _consentimientos(),
        },
    )
    assert r.status_code == 201, r.text
    return dni


def _capturar_email(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    from tarjeta.modules.identidad.infrastructure.email_consola import EmailConsola

    capturado: dict[str, str] = {}

    async def _captura(self: object, email: str, asunto: str, cuerpo: str) -> None:
        capturado["email"] = email
        capturado["cuerpo"] = cuerpo

    monkeypatch.setattr(EmailConsola, "enviar", _captura)
    return capturado


async def test_recuperacion_cambia_password_y_cierra_sesiones(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    capturado = _capturar_email(monkeypatch)
    email = f"vecino-{random.randint(1, 1_000_000)}@example.com"
    dni = await _registrar_con_email(client, email)
    refresh_viejo = (await _login(client, dni))["refresh_token"]

    # 1) Solicitar: siempre 202, y se "envía" el token por email (capturado en el test).
    r = await client.post("/api/v1/auth/recuperar", json={"email": email})
    assert r.status_code == 202
    token = capturado["cuerpo"].rsplit(": ", 1)[1].strip()

    # 2) Confirmar con la contraseña nueva.
    nueva = "nueva-contrasena-999"
    r = await client.post(
        "/api/v1/auth/recuperar/confirmar", json={"token": token, "password": nueva}
    )
    assert r.status_code == 200, r.text

    # El refresh anterior quedó revocado (se cerraron las sesiones).
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_viejo})
    assert r.status_code == 401
    # La contraseña vieja ya no sirve; la nueva sí.
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": PASSWORD})
    assert r.status_code == 401
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": nueva})
    assert r.status_code == 200

    # El token es de un solo uso: reutilizarlo falla.
    r = await client.post(
        "/api/v1/auth/recuperar/confirmar", json={"token": token, "password": "otra-larga-123"}
    )
    assert r.status_code == 422


async def test_recuperar_no_revela_si_el_email_existe(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/recuperar", json={"email": "no-existe@example.com"})
    assert r.status_code == 202
    assert "instrucciones" in r.json()["mensaje"].lower()


async def test_recuperar_token_invalido_falla(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/recuperar/confirmar",
        json={"token": "token-inexistente", "password": "contrasena-larga-123"},
    )
    assert r.status_code == 422


async def test_recuperar_password_debil_no_quema_el_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    capturado = _capturar_email(monkeypatch)
    email = f"vecino-{random.randint(1, 1_000_000)}@example.com"
    await _registrar_con_email(client, email)
    await client.post("/api/v1/auth/recuperar", json={"email": email})
    token = capturado["cuerpo"].rsplit(": ", 1)[1].strip()

    # Contraseña muy corta: 422 y el token NO se consume.
    r = await client.post(
        "/api/v1/auth/recuperar/confirmar", json={"token": token, "password": "corta"}
    )
    assert r.status_code == 422
    # El mismo token sigue sirviendo con una contraseña válida.
    r = await client.post(
        "/api/v1/auth/recuperar/confirmar",
        json={"token": token, "password": "contrasena-valida-123"},
    )
    assert r.status_code == 200, r.text


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
