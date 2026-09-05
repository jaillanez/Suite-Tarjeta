"""Integración: comercios — adhesión, sucursales PostGIS, cajero, bandeja municipal.

Requiere PostgreSQL real (con PostGIS) y Redis.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

pytestmark = pytest.mark.integration

import jwt  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402
from tarjeta.modules.gobierno.application.sync_agente import desactivar_agente  # noqa: E402
from tarjeta.shared.infrastructure.outbox import EventDispatcher, OutboxModel  # noqa: E402

PASSWORD = "contrasena-larga-123"


def _cuit() -> str:
    # §13.1: sin paridad. Si es comerciante se siembra en el padrón (fixture `padron`).
    return f"20{random.randint(10_000_000, 39_999_999)}1"  # 11 dígitos


def _token(id_persona: str, perfil: str) -> str:
    settings = get_settings()
    payload = {"sub": id_persona, "perfil": perfil, "permisos": []}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sub(access_token: str) -> str:
    settings = get_settings()
    data = jwt.decode(access_token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
    return str(data["sub"])


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
    await redis.flushdb()  # resetea rate limiters entre tests
    await engine.dispose()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await redis.aclose()


async def _registrar(client: AsyncClient) -> str:
    dni = str(random.randint(10_000_000, 39_999_999))
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
    return _sub(r.json()["tokens"]["access_token"])


async def _adherir(
    client: AsyncClient, padron, *, comerciante: bool = True, sucursal: dict | None = None
):
    id_persona = await _registrar(client)
    ciudadano = _token(id_persona, "CIUDADANO")
    cuit = _cuit()
    padron.comerciante(cuit, comerciante)
    body = {
        "cuit": cuit,
        "razon_social": "Kiosco Rivadavia",
        "nombre_fantasia": "El Kiosco",
        "rubro": "kiosco",
        "convenio_version": "v1",
        "sucursal": sucursal
        or {"nombre": "Central", "direccion": "San Isidro 123", "lat": -31.536, "lon": -68.398},
    }
    r = await client.post(
        "/api/v1/portal-comercio/adhesion", headers=_headers(ciudadano), json=body
    )
    return id_persona, r


# --------------------------------------------------------------- adhesión


async def test_cuit_no_comerciante_no_adhiere(client: AsyncClient, padron) -> None:
    _, r = await _adherir(client, padron, comerciante=False)
    assert r.status_code == 409, r.text


async def test_adhesion_ok_y_mi_comercio(client: AsyncClient, padron) -> None:
    id_persona, r = await _adherir(client, padron, comerciante=True)
    assert r.status_code == 200, r.text
    id_comercio = r.json()["id_comercio"]
    comercio_token = _token(id_persona, f"COMERCIO:{id_comercio}")
    r = await client.get("/api/v1/comercios/mi-comercio", headers=_headers(comercio_token))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "SOLICITADA"


# --------------------------------------------------------------- sucursales PostGIS


async def _activar_comercio(client: AsyncClient, id_comercio: str) -> None:
    # §12.1: el comercio solo aparece en el mapa una vez aprobado/activo.
    agente = str(uuid.uuid4())
    await _seed_agente(agente, "ADMINISTRADOR")
    hm = _headers(_token(agente, "MUNICIPAL"))
    await client.post(f"/api/v1/portal-comercio/comercios/{id_comercio}/tomar", headers=hm)
    r = await client.post(f"/api/v1/portal-comercio/comercios/{id_comercio}/aprobar", headers=hm)
    assert r.status_code == 200, r.text


async def test_cercania_ordena_por_distancia(client: AsyncClient, padron) -> None:
    id_persona, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    h = _headers(_token(id_persona, f"COMERCIO:{id_comercio}"))
    # Punto distintivo para no mezclarse con sucursales de otros tests (que están en ~-31.53).
    cerca = {"nombre": "Cerca", "direccion": "a", "lat": -31.9000, "lon": -68.9000}
    lejos = {"nombre": "Lejos", "direccion": "b", "lat": -31.9300, "lon": -68.9300}
    id_cerca = (await client.post("/api/v1/comercios/sucursales", headers=h, json=cerca)).json()[
        "mensaje"
    ]
    id_lejos = (await client.post("/api/v1/comercios/sucursales", headers=h, json=lejos)).json()[
        "mensaje"
    ]
    await _activar_comercio(client, id_comercio)

    r = await client.get(
        "/api/v1/comercios/cercanas",
        params={"lat": -31.9001, "lon": -68.9001, "radio_m": 6000, "limite": 100},
    )
    assert r.status_code == 200, r.text
    ids = [s["id"] for s in r.json()]
    assert id_cerca in ids and id_lejos in ids
    assert ids.index(id_cerca) < ids.index(id_lejos)  # orden por distancia


async def test_abierto_ahora_respeta_zona(client: AsyncClient, padron) -> None:
    settings = get_settings()
    ahora = datetime.now(ZoneInfo(settings.municipio_timezone))
    id_persona, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    h = _headers(_token(id_persona, f"COMERCIO:{id_comercio}"))
    # Sucursal abierta todo el día de hoy (según la zona del municipio).
    abierta = {
        "nombre": "Abierta",
        "direccion": "x",
        "lat": -31.53,
        "lon": -68.39,
        "horarios": [{"dia": ahora.weekday(), "franjas": [{"desde": "00:00", "hasta": "23:59"}]}],
    }
    r1 = await client.post("/api/v1/comercios/sucursales", headers=h, json=abierta)
    id_suc = r1.json()["mensaje"]
    r = await client.get(f"/api/v1/comercios/sucursales/{id_suc}/abierto-ahora")
    assert r.status_code == 200, r.text
    assert r.json()["abierto"] is True

    # Sucursal sin horarios => cerrada.
    r2 = await client.post(
        "/api/v1/comercios/sucursales",
        headers=h,
        json={"nombre": "SinHorario", "direccion": "y", "lat": -31.53, "lon": -68.39},
    )
    r = await client.get(f"/api/v1/comercios/sucursales/{r2.json()['mensaje']}/abierto-ahora")
    assert r.json()["abierto"] is False


async def test_qr_pdf(client: AsyncClient, padron) -> None:
    id_persona, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    h = _headers(_token(id_persona, f"COMERCIO:{id_comercio}"))
    r = await client.get("/api/v1/comercios/sucursales", headers=h)
    id_suc = r.json()[0]["id"]
    r = await client.get(f"/api/v1/comercios/sucursales/{id_suc}/qr.pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


# --------------------------------------------------------------- privacidad del ciudadano


_PROHIBIDOS = ("dni", "cuil", "domicilio", "celular", "email")


async def test_ningun_endpoint_expone_datos_del_ciudadano(client: AsyncClient, padron) -> None:
    id_persona, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    h = _headers(_token(id_persona, f"COMERCIO:{id_comercio}"))
    # Agente municipal para la ficha.
    pid_muni = str(uuid.uuid4())
    await _seed_agente(pid_muni, "ADMINISTRADOR")
    hm = _headers(_token(pid_muni, "MUNICIPAL"))

    respuestas = [
        (await client.get("/api/v1/comercios/mi-comercio", headers=h)).text,
        (await client.get("/api/v1/comercios/sucursales", headers=h)).text,
        (await client.get("/api/v1/comercios/usuarios", headers=h)).text,
        (
            await client.get(f"/api/v1/portal-comercio/comercios/{id_comercio}/ficha", headers=hm)
        ).text,
    ]
    for cuerpo in respuestas:
        bajo = cuerpo.lower()
        for prohibido in _PROHIBIDOS:
            assert prohibido not in bajo, f"'{prohibido}' aparece en {cuerpo[:200]}"


# --------------------------------------------------------------- cajero PIN


async def _seed_agente(id_persona: str, rol: str) -> None:
    settings = get_settings()
    eng = create_async_engine(str(settings.database_url))
    async with eng.begin() as c:
        await c.execute(
            text(
                "INSERT INTO agente_municipal (id_persona, rol, activo) VALUES (:id, :rol, true) "
                "ON CONFLICT (id_persona) DO UPDATE SET rol = :rol, activo = true"
            ),
            {"id": id_persona, "rol": rol},
        )
    await eng.dispose()


async def _invitar_y_aceptar_cajero(
    client: AsyncClient, *, admin_persona: str, id_comercio: str
) -> str:
    h_admin = _headers(_token(admin_persona, f"COMERCIO:{id_comercio}"))
    r = await client.post(
        "/api/v1/comercios/usuarios/invitar",
        headers=h_admin,
        json={"rol": "CAJERO", "destino": "cajero@example.com"},
    )
    assert r.status_code == 200, r.text
    token_inv = r.json()["token"]
    cajero_persona = await _registrar(client)
    r = await client.post(
        f"/api/v1/portal-comercio/invitaciones/{token_inv}/aceptar",
        headers=_headers(_token(cajero_persona, "CIUDADANO")),
    )
    assert r.status_code == 200, r.text
    # id del usuario_comercio del cajero
    r = await client.get("/api/v1/comercios/usuarios", headers=h_admin)
    ids = [u["id"] for u in r.json() if u["rol"] == "CAJERO"]
    return ids[0]


async def _nuevo_cajero(
    client: AsyncClient, *, admin: str, id_comercio: str, previos: set[str]
) -> tuple[str, str]:
    """Da de alta un cajero nuevo (invitación + registro + aceptación). Devuelve
    (id_usuario, id_persona). `previos` = id_usuario ya existentes, para hallar el nuevo."""
    h_admin = _headers(_token(admin, f"COMERCIO:{id_comercio}"))
    r = await client.post(
        "/api/v1/comercios/usuarios/invitar",
        headers=h_admin,
        json={"rol": "CAJERO", "destino": "cajero@example.com"},
    )
    token_inv = r.json()["token"]
    persona = await _registrar(client)
    await client.post(
        f"/api/v1/portal-comercio/invitaciones/{token_inv}/aceptar",
        headers=_headers(_token(persona, "CIUDADANO")),
    )
    r = await client.get("/api/v1/comercios/usuarios", headers=h_admin)
    ids = {u["id"] for u in r.json() if u["rol"] == "CAJERO"}
    return (ids - previos).pop(), persona


async def _registrar_pin(
    client: AsyncClient, *, admin: str, id_comercio: str, id_usuario: str, huella: str, pin: str
) -> None:
    h_admin = _headers(_token(admin, f"COMERCIO:{id_comercio}"))
    r = await client.post(
        f"/api/v1/comercios/cajeros/{id_usuario}/pin",
        headers={**h_admin, "X-Device-Huella": huella},
        json={"pin": pin},
    )
    assert r.status_code == 200, r.text


async def test_pin_no_funciona_desde_otro_dispositivo(client: AsyncClient, padron) -> None:
    admin, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    id_usuario = await _invitar_y_aceptar_cajero(
        client, admin_persona=admin, id_comercio=id_comercio
    )
    # Huellas únicas por test (el test DB no aísla filas entre tests): el registrado y "otro".
    huella_ok, huella_otro = str(uuid.uuid4()), str(uuid.uuid4())
    # El encargado registra el PIN en el dispositivo registrado.
    await _registrar_pin(
        client,
        admin=admin,
        id_comercio=id_comercio,
        id_usuario=id_usuario,
        huella=huella_ok,
        pin="1234",
    )
    # Login de ese cajero desde otro dispositivo: no pertenece a esa huella -> 403.
    r = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id_usuario, "pin": "1234"},
        headers={"X-Device-Huella": huella_otro},
    )
    assert r.status_code == 403, r.text
    # Login desde el dispositivo registrado: ok.
    r = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id_usuario, "pin": "1234"},
        headers={"X-Device-Huella": huella_ok},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


async def test_baja_cajero_revoca_sesiones(client: AsyncClient, padron) -> None:
    admin, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    id_usuario = await _invitar_y_aceptar_cajero(
        client, admin_persona=admin, id_comercio=id_comercio
    )
    h_admin = _headers(_token(admin, f"COMERCIO:{id_comercio}"))
    huella = str(uuid.uuid4())  # única por test: la caja resuelve por huella
    await _registrar_pin(
        client,
        admin=admin,
        id_comercio=id_comercio,
        id_usuario=id_usuario,
        huella=huella,
        pin="1234",
    )
    r = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id_usuario, "pin": "1234"},
        headers={"X-Device-Huella": huella},
    )
    refresh = r.json()["refresh_token"]
    # Dar de baja al cajero revoca sus sesiones.
    r = await client.post(f"/api/v1/portal-comercio/cajeros/{id_usuario}/baja", headers=h_admin)
    assert r.status_code == 200, r.text
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401  # sesión revocada


async def test_caja_lista_dispositivo_sin_cajeros(client: AsyncClient) -> None:
    # Una huella desconocida devuelve lista vacía (no revela si el dispositivo existe).
    r = await client.get(
        "/api/v1/portal-comercio/cajero/lista",
        headers={"X-Device-Huella": str(uuid.uuid4())},
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_caja_dos_cajeros_mismo_dispositivo_mismo_pin(client: AsyncClient, padron) -> None:
    admin, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    huella = str(uuid.uuid4())
    id1, p1 = await _nuevo_cajero(client, admin=admin, id_comercio=id_comercio, previos=set())
    await _registrar_pin(
        client, admin=admin, id_comercio=id_comercio, id_usuario=id1, huella=huella, pin="1234"
    )
    id2, p2 = await _nuevo_cajero(client, admin=admin, id_comercio=id_comercio, previos={id1})
    await _registrar_pin(
        client, admin=admin, id_comercio=id_comercio, id_usuario=id2, huella=huella, pin="1234"
    )
    # El selector muestra los dos y SOLO expone id y nombre corto (ningún dato personal).
    r = await client.get(
        "/api/v1/portal-comercio/cajero/lista", headers={"X-Device-Huella": huella}
    )
    assert r.status_code == 200
    lista = r.json()
    assert {c["id_usuario"] for c in lista} == {id1, id2}
    assert all(set(c) == {"id_usuario", "nombre"} for c in lista)
    # Mismo PIN, pero cada login entra como el cajero elegido, no como el otro.
    r1 = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id1, "pin": "1234"},
        headers={"X-Device-Huella": huella},
    )
    assert r1.status_code == 200, r1.text
    assert _sub(r1.json()["access_token"]) == p1
    r2 = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id2, "pin": "1234"},
        headers={"X-Device-Huella": huella},
    )
    assert r2.status_code == 200, r2.text
    assert _sub(r2.json()["access_token"]) == p2


async def test_caja_rechaza_cajero_de_otra_huella(client: AsyncClient, padron) -> None:
    admin, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    id1, _ = await _nuevo_cajero(client, admin=admin, id_comercio=id_comercio, previos=set())
    await _registrar_pin(
        client,
        admin=admin,
        id_comercio=id_comercio,
        id_usuario=id1,
        huella=str(uuid.uuid4()),
        pin="1234",
    )
    # El PIN es correcto, pero el cajero no pertenece a ESTA huella -> rechazo (no alcanza el PIN).
    r = await client.post(
        "/api/v1/portal-comercio/cajero/login",
        json={"id_usuario": id1, "pin": "1234"},
        headers={"X-Device-Huella": str(uuid.uuid4())},
    )
    assert r.status_code == 403, r.text


async def test_caja_bloquea_por_dispositivo_y_reinicia_con_exito(
    client: AsyncClient, padron
) -> None:
    admin, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    huella = str(uuid.uuid4())
    id1, _ = await _nuevo_cajero(client, admin=admin, id_comercio=id_comercio, previos=set())
    await _registrar_pin(
        client, admin=admin, id_comercio=id_comercio, id_usuario=id1, huella=huella, pin="1234"
    )
    h = {"X-Device-Huella": huella}
    login = "/api/v1/portal-comercio/cajero/login"

    # Dos fallos y luego un login correcto: el contador se reinicia.
    for _ in range(2):
        r = await client.post(login, json={"id_usuario": id1, "pin": "0000"}, headers=h)
        assert r.status_code == 422, r.text
    r = await client.post(login, json={"id_usuario": id1, "pin": "1234"}, headers=h)
    assert r.status_code == 200, r.text

    # Tras el éxito hacen falta de nuevo tres fallos: al tercero, espera de 30 s (429).
    for _ in range(2):
        r = await client.post(login, json={"id_usuario": id1, "pin": "0000"}, headers=h)
        assert r.status_code == 422, r.text
    r = await client.post(login, json={"id_usuario": id1, "pin": "0000"}, headers=h)
    assert r.status_code == 429, r.text
    assert r.headers.get("retry-after") == "30"
    # Bloqueado por dispositivo: aunque el PIN sea correcto, sigue en espera.
    r = await client.post(login, json={"id_usuario": id1, "pin": "1234"}, headers=h)
    assert r.status_code == 429, r.text


# --------------------------------------------------------------- bandeja municipal


async def test_bandeja_y_doble_conformidad_baja(client: AsyncClient, padron) -> None:
    _, r = await _adherir(client, padron, comerciante=True)
    id_comercio = r.json()["id_comercio"]
    # Dos agentes municipales (para la doble conformidad de la baja).
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    await _seed_agente(a1, "ADMINISTRADOR")
    await _seed_agente(a2, "ADMINISTRADOR")
    h1 = _headers(_token(a1, "MUNICIPAL"))
    h2 = _headers(_token(a2, "MUNICIPAL"))

    r = await client.get("/api/v1/portal-comercio/bandeja", headers=h1)
    assert r.status_code == 200
    assert any(c["id"] == id_comercio for c in r.json())

    # Aprobar el comercio (queda ACTIVA).
    await client.post(f"/api/v1/portal-comercio/comercios/{id_comercio}/tomar", headers=h1)
    r = await client.post(f"/api/v1/portal-comercio/comercios/{id_comercio}/aprobar", headers=h1)
    assert r.status_code == 200, r.text

    # Baja definitiva: solicita a1, aprueba a2 (doble conformidad).
    r = await client.post(
        f"/api/v1/portal-comercio/comercios/{id_comercio}/baja-solicitar",
        headers=h1,
        json={"motivo": "cierre"},
    )
    id_sol = r.json()["id"]
    # Autoaprobación prohibida.
    r = await client.post(
        f"/api/v1/portal-comercio/baja/{id_sol}/aprobar", headers=h1, json={"motivo": "yo"}
    )
    assert r.status_code == 409
    # Aprueba el segundo agente.
    r = await client.post(
        f"/api/v1/portal-comercio/baja/{id_sol}/aprobar", headers=h2, json={"motivo": "ok"}
    )
    assert r.status_code == 200, r.text
    r = await client.get(f"/api/v1/portal-comercio/comercios/{id_comercio}/ficha", headers=h1)
    assert r.json()["estado"] == "BAJA"


async def test_carga_masiva_valida_y_reporta(client: AsyncClient, padron) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, "ADMINISTRADOR")
    h = _headers(_token(pid, "MUNICIPAL"))
    ok1 = _cuit()
    padron.comerciante(ok1, True)
    malo = _cuit()
    padron.comerciante(malo, False)
    csv = f"cuit,razon_social,rubro\n{ok1},Comercio Uno,kiosco\n{malo},Comercio Malo,almacen\n,,\n"
    r = await client.post(
        "/api/v1/portal-comercio/carga-masiva",
        headers=h,
        json={"contenido": csv, "confirmar": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["creados"] == 1  # solo el comerciante válido
    filas = {f["fila"]: f for f in body["filas"]}
    assert filas[1]["ok"] is True
    assert filas[2]["ok"] is False  # no comerciante
    assert filas[3]["ok"] is False  # faltan datos


# --------------------------------------------------------------- deuda 06.0.B


async def test_revocar_perfil_municipal_desactiva_agente(client: AsyncClient) -> None:
    settings = get_settings()
    pid = str(uuid.uuid4())
    await _seed_agente(pid, "ADMINISTRADOR")
    h = _headers(_token(pid, "MUNICIPAL"))
    # Con el agente activo, accede al portal municipal.
    r = await client.get("/api/v1/gobierno/parametros", headers=h)
    assert r.status_code == 200, r.text

    # Evento de identidad: perfil municipal revocado -> gobierno desactiva al agente.
    eng = create_async_engine(str(settings.database_url))
    sm = async_sessionmaker(eng, expire_on_commit=False)
    dispatcher = EventDispatcher()
    dispatcher.subscribe("PerfilMunicipalRevocado", desactivar_agente)
    try:
        async with sm() as s:
            s.add(
                OutboxModel(
                    id=uuid.uuid4(),
                    tipo="PerfilMunicipalRevocado",
                    payload={"event_id": str(uuid.uuid4()), "id_persona": pid},
                    ocurrido_en=datetime.now(UTC),
                    procesado=False,
                )
            )
            await s.commit()
        async with sm() as s:
            await dispatcher.drain(s)
    finally:
        await eng.dispose()

    # Ahora el agente perdió el acceso, sin intervención manual.
    r = await client.get("/api/v1/gobierno/parametros", headers=h)
    assert r.status_code == 403
