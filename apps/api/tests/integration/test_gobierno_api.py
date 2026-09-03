"""Integración: portal municipal (gobierno) — permisos, parametría, doble conformidad,
auditoría inmutable y worker de outbox. Requiere PostgreSQL real."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.integration

import jwt  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402
from tarjeta.modules.gobierno.application.auditoria_consumer import consumir_evento  # noqa: E402
from tarjeta.modules.gobierno.domain.roles import RolMunicipal  # noqa: E402
from tarjeta.modules.gobierno.infrastructure.composition import (  # noqa: E402
    construir_puertos_gobierno,
)
from tarjeta.modules.gobierno.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyAgenteRepository,
)
from tarjeta.shared.domain.types import EntityId  # noqa: E402
from tarjeta.shared.infrastructure.outbox import (  # noqa: E402
    EventDispatcher,
    OutboxModel,
)


def _token(id_persona: str, *, perfil: str = "MUNICIPAL") -> str:
    settings = get_settings()
    payload = {"sub": id_persona, "perfil": perfil, "permisos": []}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


async def _seed_agente(id_persona: str, rol: RolMunicipal) -> None:
    settings = get_settings()
    eng = create_async_engine(str(settings.database_url))
    async with eng.begin() as c:
        await c.execute(
            text(
                "INSERT INTO agente_municipal (id_persona, rol) VALUES (:id, :rol) "
                "ON CONFLICT (id_persona) DO UPDATE SET rol = :rol"
            ),
            {"id": id_persona, "rol": rol.value},
        )
    await eng.dispose()


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
    await engine.dispose()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------- permisos / matriz


async def test_sin_token_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/gobierno/parametros")
    assert r.status_code == 401


async def test_perfil_no_municipal_403(client: AsyncClient) -> None:
    token = _token(str(uuid.uuid4()), perfil="CIUDADANO")
    r = await client.get("/api/v1/gobierno/parametros", headers=_headers(token))
    assert r.status_code == 403


async def test_municipal_sin_rol_asignado_403(client: AsyncClient) -> None:
    # perfil municipal pero sin fila en agente_municipal -> sin permisos.
    token = _token(str(uuid.uuid4()))
    r = await client.get("/api/v1/gobierno/parametros", headers=_headers(token))
    assert r.status_code == 403


async def test_administrador_lee_y_edita_parametros(client: AsyncClient) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.ADMINISTRADOR)
    h = _headers(_token(pid))

    r = await client.get("/api/v1/gobierno/parametros", headers=h)
    assert r.status_code == 200, r.text
    assert set(r.json()) >= {"grupo_max_miembros", "puntos_vencimiento_meses"}

    r = await client.put(
        "/api/v1/gobierno/parametros/grupo_max_miembros",
        headers=h,
        json={"valor": 9, "motivo": "ajuste"},
    )
    assert r.status_code == 200, r.text

    r = await client.get("/api/v1/gobierno/parametros", headers=h)
    assert r.json()["grupo_max_miembros"] == 9  # round-trip del valor recién guardado


async def test_parametro_fuera_de_rango_422(client: AsyncClient) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.ADMINISTRADOR)
    r = await client.put(
        "/api/v1/gobierno/parametros/grupo_max_miembros",
        headers=_headers(_token(pid)),
        json={"valor": 999},
    )
    assert r.status_code == 422


async def test_auditor_no_puede_editar_pero_ve_auditoria(client: AsyncClient) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.AUDITOR)
    h = _headers(_token(pid))
    # AUDITOR no tiene PARAMETRIA_EDITAR
    r = await client.put(
        "/api/v1/gobierno/parametros/grupo_max_miembros", headers=h, json={"valor": 5}
    )
    assert r.status_code == 403
    # pero sí AUDITORIA_VER
    r = await client.get("/api/v1/gobierno/auditoria", headers=h)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


async def test_personal_no_ve_auditoria(client: AsyncClient) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.PERSONAL)
    r = await client.get("/api/v1/gobierno/auditoria", headers=_headers(_token(pid)))
    assert r.status_code == 403


async def test_recaudacion_y_agentes(client: AsyncClient) -> None:
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.ADMINISTRADOR)
    h = _headers(_token(pid))

    r = await client.get("/api/v1/gobierno/recaudacion", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "transiciones_a_black_post_registro" in body
    assert "distribucion_por_nivel" in body

    r = await client.get("/api/v1/gobierno/agentes", headers=h)
    assert r.status_code == 200
    assert any(a["id_persona"] == pid for a in r.json())


# --------------------------------------------------------------------- doble conformidad


async def test_doble_conformidad_flujo_completo(client: AsyncClient) -> None:
    # Ambos con permiso de aprobar: así se puede ejercitar la autoaprobación prohibida (409),
    # que de otro modo quedaría tapada por la puerta de permisos.
    solicitante = str(uuid.uuid4())
    aprobador = str(uuid.uuid4())
    await _seed_agente(solicitante, RolMunicipal.ADMINISTRADOR)
    await _seed_agente(aprobador, RolMunicipal.ADMINISTRADOR)

    # el administrador solicita editar una regla de nivel (🔒 doble conformidad)
    r = await client.post(
        "/api/v1/gobierno/aprobaciones",
        headers=_headers(_token(solicitante)),
        json={
            "accion": "reglas_nivel:editar",
            "payload": {"clave": "grupo_max_miembros", "valor": 7},
        },
    )
    assert r.status_code == 200, r.text
    id_sol = r.json()["id"]

    # aparece en la bandeja del aprobador
    r = await client.get("/api/v1/gobierno/aprobaciones", headers=_headers(_token(aprobador)))
    assert any(s["id"] == id_sol for s in r.json())

    # autoaprobación prohibida: el solicitante no puede aprobar (409)
    r = await client.post(
        f"/api/v1/gobierno/aprobaciones/{id_sol}/aprobar",
        headers=_headers(_token(solicitante)),
        json={"motivo": "yo mismo"},
    )
    assert r.status_code == 409

    # el administrador aprueba y se ejecuta el cambio de parámetro
    r = await client.post(
        f"/api/v1/gobierno/aprobaciones/{id_sol}/aprobar",
        headers=_headers(_token(aprobador)),
        json={"motivo": "ok"},
    )
    assert r.status_code == 200, r.text

    # el parámetro quedó en 7
    r = await client.get("/api/v1/gobierno/parametros", headers=_headers(_token(aprobador)))
    assert r.json()["grupo_max_miembros"] == 7


async def test_rechazo_de_solicitud(client: AsyncClient) -> None:
    solicitante = str(uuid.uuid4())
    aprobador = str(uuid.uuid4())
    await _seed_agente(solicitante, RolMunicipal.ENCARGADO)
    await _seed_agente(aprobador, RolMunicipal.ADMINISTRADOR)
    r = await client.post(
        "/api/v1/gobierno/aprobaciones",
        headers=_headers(_token(solicitante)),
        json={"accion": "datos:exportar_masivo", "payload": {}},
    )
    id_sol = r.json()["id"]
    r = await client.post(
        f"/api/v1/gobierno/aprobaciones/{id_sol}/rechazar",
        headers=_headers(_token(aprobador)),
        json={"motivo": "no corresponde"},
    )
    assert r.status_code == 200, r.text


# --------------------------------------------------------------------- auditoría inmutable


async def test_auditoria_inmutable_a_nivel_db(client: AsyncClient) -> None:
    # Genera una fila de auditoría vía una edición de parámetro.
    pid = str(uuid.uuid4())
    await _seed_agente(pid, RolMunicipal.ADMINISTRADOR)
    r = await client.put(
        "/api/v1/gobierno/parametros/grupo_max_altas_anuales",
        headers=_headers(_token(pid)),
        json={"valor": 3, "motivo": "test inmutabilidad"},
    )
    assert r.status_code == 200, r.text

    settings = get_settings()  # database_url -> rol tarjeta_app (runtime)
    eng = create_async_engine(str(settings.database_url))
    try:
        # El rol de runtime NO puede modificar ni borrar auditoría.
        with pytest.raises(Exception) as exc_update:
            async with eng.begin() as c:
                await c.execute(text("UPDATE registro_auditoria SET accion = 'hackeado'"))
        assert "permission denied" in str(exc_update.value).lower()

        with pytest.raises(Exception) as exc_delete:
            async with eng.begin() as c:
                await c.execute(text("DELETE FROM registro_auditoria"))
        assert "permission denied" in str(exc_delete.value).lower()
    finally:
        await eng.dispose()


# --------------------------------------------------------------------- worker de outbox


async def test_worker_procesa_evento_sin_http_y_redacta_pii(client: AsyncClient) -> None:
    """El dispatcher drena el outbox fuera de cualquier request y la auditoría no guarda PII."""
    settings = get_settings()
    eng = create_async_engine(str(settings.database_url))
    sm = async_sessionmaker(eng, expire_on_commit=False)
    dispatcher = EventDispatcher()
    dispatcher.subscribe_all(consumir_evento)

    evento_id = str(uuid.uuid4())
    id_persona = str(uuid.uuid4())
    try:
        # Inserta un evento con un DNI en el payload directamente en el outbox.
        async with sm() as s:
            s.add(
                OutboxModel(
                    id=uuid.uuid4(),
                    tipo="PruebaEvento",
                    payload={"event_id": evento_id, "id_persona": id_persona, "dni": "12345678"},
                    ocurrido_en=datetime.now(UTC),
                    procesado=False,
                )
            )
            await s.commit()

        async with sm() as s:
            procesados = await dispatcher.drain(s)
        assert procesados >= 1

        # Segunda pasada: idempotente (no re-audita, no re-procesa el mismo evento marcado).
        async with sm() as s:
            await dispatcher.drain(s)

        # La auditoría existe (una sola vez pese a los dos drains) y sin DNI en claro.
        async with sm() as s:
            puertos = construir_puertos_gobierno(s)
            registros = await puertos.auditoria.listar(
                actor=None, accion="PruebaEvento", entidad=None, limite=200, offset=0
            )
        mios = [r for r in registros if r.id_evento_origen == evento_id]
        assert len(mios) == 1  # idempotencia: no se auditó dos veces el mismo evento
        assert "12345678" not in str(mios[0].valor_nuevo)
    finally:
        await eng.dispose()


# --------------------------------------------------------------------- repos directos


async def test_agente_repo_asignar_y_listar(client: AsyncClient) -> None:
    settings = get_settings()
    eng = create_async_engine(str(settings.database_url))
    sm = async_sessionmaker(eng, expire_on_commit=False)
    pid = EntityId.new()
    try:
        async with sm() as s:
            repo = SqlAlchemyAgenteRepository(s)
            await repo.asignar(pid, RolMunicipal.SUPER_ADMIN)
            await s.commit()
            assert await repo.rol_de(pid) is RolMunicipal.SUPER_ADMIN
            assert (str(pid), RolMunicipal.SUPER_ADMIN) in await repo.listar()
    finally:
        await eng.dispose()
