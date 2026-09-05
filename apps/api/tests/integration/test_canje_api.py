"""Integración: canje — topes por usuario/día, flujo completo, idempotencia, offline.

Requiere PostgreSQL real y Redis.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import pytest

pytestmark = pytest.mark.integration

import jwt  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.main import create_app  # noqa: E402
from tarjeta.modules.canje.application.operaciones import (  # noqa: E402
    AnularOperacion,
    DecidirOperacion,
    ExpirarPendientes,
    IniciarOperacion,
)
from tarjeta.modules.canje.domain.ports import ReservaPromocion  # noqa: E402
from tarjeta.modules.canje.domain.transaccion import Confirmador, ViaCanje  # noqa: E402
from tarjeta.modules.canje.infrastructure.composition import construir_puertos_canje  # noqa: E402
from tarjeta.modules.comercios.domain.comercio import (  # noqa: E402
    Comercio,
    EstadoComercio,
    EvidenciaConvenio,
)
from tarjeta.modules.comercios.domain.roles import RolComercio  # noqa: E402
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio  # noqa: E402
from tarjeta.modules.comercios.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyComercioRepository,
    SqlAlchemyUsuarioComercioRepository,
)
from tarjeta.modules.promociones.domain.errors import TopeAgotado  # noqa: E402
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento  # noqa: E402
from tarjeta.modules.promociones.domain.promocion import Promocion  # noqa: E402
from tarjeta.modules.promociones.domain.vigencia import Vigencia  # noqa: E402
from tarjeta.modules.promociones.infrastructure.composition import (  # noqa: E402
    construir_puertos_promociones,
)
from tarjeta.modules.promociones.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyPromocionRepository,
)
from tarjeta.shared.domain.errors import NotFoundError  # noqa: E402
from tarjeta.shared.domain.types import EntityId  # noqa: E402

PASSWORD = "contrasena-larga-123"


class _Reserva(ReservaPromocion):
    def __init__(self, session: object) -> None:
        self._repo = SqlAlchemyPromocionRepository(session)  # type: ignore[arg-type]

    async def reservar(self, id_promocion: str, id_persona: str, fecha: date) -> None:
        await self._repo.reservar_uso(
            EntityId.from_str(id_promocion), EntityId.from_str(id_persona), fecha
        )

    async def liberar(self, id_promocion: str, id_persona: str, fecha: date) -> None:
        await self._repo.liberar_uso(
            EntityId.from_str(id_promocion), EntityId.from_str(id_persona), fecha
        )


def _canje(session: object):
    return construir_puertos_canje(session, _Reserva(session))  # type: ignore[arg-type]


@pytest.fixture
async def sm() -> AsyncIterator[async_sessionmaker]:
    eng = create_async_engine(str(get_settings().database_url))
    try:
        async with eng.connect() as c:
            await c.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await eng.dispose()
        pytest.skip(f"Base no disponible: {exc}")
    yield async_sessionmaker(eng, expire_on_commit=False)
    await eng.dispose()


def _vig() -> Vigencia:
    return Vigencia(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2027, 12, 31))


async def _promo_activa(
    sm: async_sessionmaker,
    *,
    id_sucursal: str,
    tope_total: int | None = None,
    tope_por_usuario: int | None = None,
    tope_por_dia: int | None = None,
) -> str:
    async with sm() as s:
        promo = Promocion.crear(
            id_comercio=EntityId.new(),
            titulo="Promo canje",
            descripcion="",
            mecanica=Mecanica.PORCENTAJE,
            segmento=Segmento.AMBOS,
            valor_platino=10,
            valor_black=20,
            vigencia=_vig(),
            sucursales=[EntityId.from_str(id_sucursal)],
            tope_total=tope_total,
            tope_por_usuario=tope_por_usuario,
            tope_por_dia=tope_por_dia,
        )
        promo.activar()
        await construir_puertos_promociones(s).promociones.agregar(promo)
        await s.commit()
        return str(promo.id)


# --------------------------------------------------------------- deuda A: topes usuario/día


async def test_concurrencia_tope_por_usuario(sm: async_sessionmaker) -> None:
    M, N = 20, 100
    suc = str(uuid.uuid4())
    persona = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_por_usuario=M)
    hoy = datetime.now(UTC).date()

    async def reservar() -> bool:
        async with sm() as s:
            try:
                await _Reserva(s).reservar(pid, persona, hoy)
                await s.commit()
                return True
            except TopeAgotado:
                return False

    otorgados = sum(await asyncio.gather(*(reservar() for _ in range(N))))
    assert otorgados == M, f"esperados {M}, otorgados {otorgados}"


async def test_concurrencia_tope_por_dia(sm: async_sessionmaker) -> None:
    M, N = 15, 80
    suc = str(uuid.uuid4())
    persona = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_por_dia=M)
    hoy = datetime.now(UTC).date()

    async def reservar() -> bool:
        async with sm() as s:
            try:
                await _Reserva(s).reservar(pid, persona, hoy)
                await s.commit()
                return True
            except TopeAgotado:
                return False

    otorgados = sum(await asyncio.gather(*(reservar() for _ in range(N))))
    assert otorgados == M


# --------------------------------------------------------------- idempotencia / confirmación


def _iniciar_caso(puertos):
    return IniciarOperacion(puertos, prefijo_comprobante="RIV", ttl_confirmacion_seg=90)


async def _iniciar(
    sm: async_sessionmaker, *, suc: str, pid: str, persona: str, clave: str, monto=1000
):
    async with sm() as s:
        return await _iniciar_caso(_canje(s)).ejecutar(
            id_persona=persona,
            nivel="BLACK",
            id_comercio=str(uuid.uuid4()),
            id_sucursal=suc,
            id_cajero=str(uuid.uuid4()),
            id_promocion=pid,
            mecanica="PORCENTAJE",
            valor=20,
            monto=monto,
            via=ViaCanje.CAJERO_ESCANEA,
            clave_idempotencia=clave,
        )


async def test_idempotencia_misma_clave_una_operacion(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    clave = f"idem-{uuid.uuid4()}"
    t1 = await _iniciar(sm, suc=suc, pid=pid, persona=persona, clave=clave)
    t2 = await _iniciar(sm, suc=suc, pid=pid, persona=persona, clave=clave)
    assert str(t1.id) == str(t2.id)  # misma operación
    assert t1.descuento == 200  # 20% de 1000
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.usos_totales == 1  # una sola reserva


async def test_confirmacion_aplica_y_sin_confirmacion_no(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    t = await _iniciar(sm, suc=suc, pid=pid, persona=persona, clave=f"c-{uuid.uuid4()}")
    assert t.estado.value == "PENDIENTE_CONFIRMACION"  # nada aplicado aún
    async with sm() as s:
        aplicada = await DecidirOperacion(_canje(s)).confirmar(
            id_transaccion=str(t.id), por=Confirmador.CIUDADANO, id_actor=persona
        )
    assert aplicada.estado.value == "APLICADA"


async def test_expiracion_libera_reserva(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    t = await _iniciar(sm, suc=suc, pid=pid, persona=persona, clave=f"e-{uuid.uuid4()}")
    # Forzar el vencimiento.
    async with sm() as s:
        await s.execute(
            text("UPDATE transaccion SET vence_en = :v WHERE id = :id"),
            {"v": datetime.now(UTC).replace(year=2020), "id": t.id.value},
        )
        await s.commit()
    async with sm() as s:
        n = await ExpirarPendientes(_canje(s)).ejecutar()
    assert n >= 1
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.usos_totales == 0  # se liberó la reserva


async def test_anulacion_revierte_tope(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    t = await _iniciar(sm, suc=suc, pid=pid, persona=persona, clave=f"a-{uuid.uuid4()}")
    async with sm() as s:
        await DecidirOperacion(_canje(s)).confirmar(
            id_transaccion=str(t.id), por=Confirmador.CIUDADANO, id_actor=persona
        )
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.usos_totales == 1
    async with sm() as s:
        await AnularOperacion(_canje(s), ventana_minutos=15).ejecutar(
            id_transaccion=str(t.id), motivo="error", es_admin=False
        )
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.usos_totales == 0  # tope revertido


# --------------------------------------------------------------- P1-E: IDOR entre comercios


async def _iniciar_para(
    sm: async_sessionmaker, *, suc: str, pid: str, persona: str, id_comercio: str, via: ViaCanje
):
    async with sm() as s:
        return await _iniciar_caso(_canje(s)).ejecutar(
            id_persona=persona,
            nivel="BLACK",
            id_comercio=id_comercio,
            id_sucursal=suc,
            id_cajero=str(uuid.uuid4()),
            id_promocion=pid,
            mecanica="PORCENTAJE",
            valor=20,
            monto=1000,
            via=via,
            clave_idempotencia=f"idor-{uuid.uuid4()}",
        )


async def test_anular_de_otro_comercio_es_inexistente(sm: async_sessionmaker) -> None:
    # §12-P1-E (IDOR): un comercio no puede anular la operación aplicada de otro comercio.
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    comercio_a = str(uuid.uuid4())
    t = await _iniciar_para(
        sm, suc=suc, pid=pid, persona=persona, id_comercio=comercio_a, via=ViaCanje.CAJERO_ESCANEA
    )
    async with sm() as s:
        await DecidirOperacion(_canje(s)).confirmar(
            id_transaccion=str(t.id), por=Confirmador.CIUDADANO, id_actor=persona
        )
    # Otro comercio: no la ve (se responde como inexistente, sin filtrar su existencia).
    async with sm() as s:
        with pytest.raises(NotFoundError):
            await AnularOperacion(_canje(s), ventana_minutos=15).ejecutar(
                id_transaccion=str(t.id),
                motivo="ajeno",
                es_admin=False,
                id_comercio=str(uuid.uuid4()),
            )
    # El comercio dueño sí puede (control positivo).
    async with sm() as s:
        await AnularOperacion(_canje(s), ventana_minutos=15).ejecutar(
            id_transaccion=str(t.id), motivo="propia", es_admin=False, id_comercio=comercio_a
        )
    async with sm() as s:
        tt = await _canje(s).transacciones.obtener(EntityId.from_str(str(t.id)))
        assert tt is not None and tt.estado.value == "ANULADA"


async def test_confirmar_de_otro_comercio_es_inexistente(sm: async_sessionmaker) -> None:
    # §12-P1-E (IDOR): un comercio no puede confirmar la operación pendiente de otro comercio.
    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=100)
    persona = str(uuid.uuid4())
    comercio_a = str(uuid.uuid4())
    # CIUDADANO_ESCANEA => la confirma el CAJERO del comercio.
    t = await _iniciar_para(
        sm,
        suc=suc,
        pid=pid,
        persona=persona,
        id_comercio=comercio_a,
        via=ViaCanje.CIUDADANO_ESCANEA,
    )
    assert t.confirmador is Confirmador.CAJERO
    async with sm() as s:
        with pytest.raises(NotFoundError):
            await DecidirOperacion(_canje(s)).confirmar(
                id_transaccion=str(t.id), por=Confirmador.CAJERO, id_comercio=str(uuid.uuid4())
            )
    async with sm() as s:
        aplicada = await DecidirOperacion(_canje(s)).confirmar(
            id_transaccion=str(t.id), por=Confirmador.CAJERO, id_comercio=comercio_a
        )
    assert aplicada.estado.value == "APLICADA"


# --------------------------------------------------------------- offline (§08.5)


async def test_offline_honra_al_ciudadano_si_se_agoto_el_tope(sm: async_sessionmaker) -> None:
    from tarjeta.modules.canje.application.sincronizacion import (
        OperacionEncolada,
        SincronizarSinConexion,
    )

    suc = str(uuid.uuid4())
    pid = await _promo_activa(sm, id_sucursal=suc, tope_total=1)  # cupo de 1
    # Agotar el tope "desde otro lado".
    async with sm() as s:
        await _Reserva(s).reservar(pid, str(uuid.uuid4()), datetime.now(UTC).date())
        await s.commit()
    # Operación encolada offline sobre la misma promo (ya agotada).
    encolada = OperacionEncolada(
        clave_idempotencia=f"off-{uuid.uuid4()}",
        id_persona=str(uuid.uuid4()),
        nivel="BLACK",
        id_comercio=str(uuid.uuid4()),
        id_sucursal=suc,
        id_cajero=str(uuid.uuid4()),
        id_promocion=pid,
        mecanica="PORCENTAJE",
        valor=20,
        monto=1000,
        via="CODIGO",
    )
    async with sm() as s:
        resultados = await SincronizarSinConexion(
            _canje(s), prefijo_comprobante="RIV", monto_max=50000, max_operaciones=50
        ).ejecutar([encolada])
    assert resultados[0].aplicada is True  # se honra al ciudadano
    assert resultados[0].conflicto_tope is True  # y se avisa el conflicto


async def test_offline_tope_de_monto(sm: async_sessionmaker) -> None:
    from tarjeta.modules.canje.application.sincronizacion import (
        OperacionEncolada,
        SincronizarSinConexion,
    )

    suc = str(uuid.uuid4())
    encolada = OperacionEncolada(
        clave_idempotencia=f"big-{uuid.uuid4()}",
        id_persona=str(uuid.uuid4()),
        nivel="BLACK",
        id_comercio=str(uuid.uuid4()),
        id_sucursal=suc,
        id_cajero=str(uuid.uuid4()),
        id_promocion=None,
        mecanica=None,
        valor=0,
        monto=999_999,  # supera el tope de monto sin conexión
        via="CODIGO",
    )
    async with sm() as s:
        resultados = await SincronizarSinConexion(
            _canje(s), prefijo_comprobante="RIV", monto_max=50000, max_operaciones=50
        ).ejecutar([encolada])
    assert resultados[0].aplicada is False
    assert "límite" in resultados[0].motivo


# --------------------------------------------------------------- HTTP: flujo completo + no PII


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


def _token(id_persona: str, perfil: str) -> str:
    payload = {"sub": id_persona, "perfil": perfil, "permisos": []}
    return jwt.encode(payload, get_settings().jwt_secret.get_secret_value(), algorithm="HS256")


def _h(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def _registrar(client: AsyncClient, padron, *, al_dia: bool = True) -> str:
    # §13.1: el nivel se controla sembrando el padrón (al_dia=True => BLACK; False => PLATINO).
    dni = str(random.randint(10_000_000, 39_999_999))
    padron.al_dia(dni, al_dia)
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
    data = jwt.decode(
        r.json()["tokens"]["access_token"],
        get_settings().jwt_secret.get_secret_value(),
        algorithms=["HS256"],
    )
    return str(data["sub"])


async def _seed_cajero_y_promo(sm: async_sessionmaker) -> tuple[str, str, str, str]:
    id_comercio = str(uuid.uuid4())
    id_sucursal = str(uuid.uuid4())
    cajero_persona = str(uuid.uuid4())
    async with sm() as s:
        # §12.1: el comercio debe existir y estar habilitado (ACTIVA) para operar canjes.
        comercio = Comercio(
            id=EntityId.from_str(id_comercio),
            cuit=str(uuid.uuid4().int)[:11],
            razon_social="Comercio Test SA",
            nombre_fantasia="La Nona",
            rubro="gastronomia",
            logo_url="",
            id_responsable=EntityId.new(),
            estado=EstadoComercio.ACTIVA,
            convenio=EvidenciaConvenio(version="v1", fecha=datetime.now(UTC), ip="1.1.1.1"),
            creado_en=datetime.now(UTC),
        )
        await SqlAlchemyComercioRepository(s).agregar(comercio)
        usuario = UsuarioComercio.crear(
            id_comercio=EntityId.from_str(id_comercio),
            id_persona=EntityId.from_str(cajero_persona),
            rol=RolComercio.CAJERO,
        )
        await SqlAlchemyUsuarioComercioRepository(s).agregar(usuario)
        await s.commit()
    pid = await _promo_activa(sm, id_sucursal=id_sucursal, tope_total=100)
    return id_comercio, id_sucursal, cajero_persona, pid


_PROHIBIDOS = ("dni", "cuil", "domicilio", "celular", "email")


async def test_flujo_http_completo_y_sin_pii(
    client: AsyncClient, sm: async_sessionmaker, padron
) -> None:
    ciudadano = await _registrar(client, padron)
    id_comercio, id_sucursal, cajero_persona, pid = await _seed_cajero_y_promo(sm)
    h_ciudadano = _h(_token(ciudadano, "CIUDADANO"))
    h_cajero = _h(_token(cajero_persona, f"COMERCIO:{id_comercio}"))

    # 1) El ciudadano pregenera sus QR (2 h).
    r = await client.get("/api/v1/canje/mis-tokens", headers=h_ciudadano)
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert len(tokens) > 100  # ~160 para 2 h
    qr = tokens[0]["token"]

    # 2) El cajero inicia la operación escaneando el QR.
    clave = f"http-{uuid.uuid4()}"
    cuerpo = {
        "via": "CAJERO_ESCANEA",
        "monto": 1000,
        "id_sucursal": id_sucursal,
        "clave_idempotencia": clave,
        "id_promocion": pid,
        "token": qr,
    }
    r = await client.post("/api/v1/canje/iniciar", headers=h_cajero, json=cuerpo)
    assert r.status_code == 200, r.text
    op = r.json()
    assert op["estado"] == "PENDIENTE_CONFIRMACION"
    assert op["total_pagar"] == 800

    # 3) Idempotencia: misma clave => misma operación.
    r2 = await client.post("/api/v1/canje/iniciar", headers=h_cajero, json=cuerpo)
    assert r2.json()["id"] == op["id"]

    # 4) Token consumido: reintentar con el MISMO QR y otra clave => rechazado.
    r3 = await client.post(
        "/api/v1/canje/iniciar",
        headers=h_cajero,
        json={**cuerpo, "clave_idempotencia": f"http-{uuid.uuid4()}"},
    )
    assert r3.status_code == 409, r3.text  # TokenYaUsado

    # 5) El ciudadano ve el pendiente y confirma.
    r = await client.get("/api/v1/canje/mis-pendientes", headers=h_ciudadano)
    assert any(o["id"] == op["id"] for o in r.json())
    r = await client.post(f"/api/v1/canje/{op['id']}/confirmar", headers=h_ciudadano)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APLICADA"

    # 6) Ningún cuerpo de respuesta expone datos personales del ciudadano al comercio.
    r = await client.get("/api/v1/canje/mis-tokens", headers=h_ciudadano)
    qr2 = r.json()[0]["token"]
    resolver_txt = (
        await client.post(
            "/api/v1/canje/resolver",
            headers=h_cajero,
            json={"via": "CAJERO_ESCANEA", "monto": 500, "id_sucursal": id_sucursal, "token": qr2},
        )
    ).text
    historial_txt = (await client.get("/api/v1/canje/historial", headers=h_ciudadano)).text
    for cuerpo_txt in (resolver_txt, historial_txt):
        bajo = cuerpo_txt.lower()
        for prohibido in _PROHIBIDOS:
            assert prohibido not in bajo, f"'{prohibido}' aparece en {cuerpo_txt[:200]}"


async def test_ciudadano_platino_canjea(
    client: AsyncClient, sm: async_sessionmaker, padron
) -> None:
    # §12.1: un ciudadano con al_dia=false (PLATINO) canjea con normalidad.
    ciudadano = await _registrar(client, padron, al_dia=False)
    id_comercio, id_sucursal, cajero_persona, pid = await _seed_cajero_y_promo(sm)
    h_caj = _h(_token(cajero_persona, f"COMERCIO:{id_comercio}"))
    h_ciu = _h(_token(ciudadano, "CIUDADANO"))
    qr = (await client.get("/api/v1/canje/mis-tokens", headers=h_ciu)).json()[0]["token"]
    cuerpo = {
        "via": "CAJERO_ESCANEA",
        "monto": 1000,
        "id_sucursal": id_sucursal,
        "clave_idempotencia": f"pl-{uuid.uuid4()}",
        "id_promocion": pid,
        "token": qr,
    }
    r = await client.post("/api/v1/canje/iniciar", headers=h_caj, json=cuerpo)
    assert r.status_code == 200, r.text
    op = r.json()
    assert op["nivel_aplicado"] == "PLATINO"
    assert op["total_pagar"] == 900  # 10% Platino de 1000
    r = await client.post(f"/api/v1/canje/{op['id']}/confirmar", headers=h_ciu)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APLICADA"
