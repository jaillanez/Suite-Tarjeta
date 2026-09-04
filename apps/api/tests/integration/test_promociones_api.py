"""Integración: promociones — concurrencia de topes, motor de resolución, búsqueda, feed.

Requiere PostgreSQL real (con pg_trgm/unaccent) y Redis.
"""

from __future__ import annotations

import asyncio
import time as _time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import insert, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.modules.promociones.application.descubrimiento import Descubrimiento  # noqa: E402
from tarjeta.modules.promociones.application.gestion import GestionPromociones  # noqa: E402
from tarjeta.modules.promociones.application.publicacion import (  # noqa: E402
    ModerarPromocion,
    PublicarPromocion,
)
from tarjeta.modules.promociones.application.reserva import ReservarUso  # noqa: E402
from tarjeta.modules.promociones.application.resolucion import MotorResolucion  # noqa: E402
from tarjeta.modules.promociones.domain.errors import TopeAgotado  # noqa: E402
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento  # noqa: E402
from tarjeta.modules.promociones.domain.ports import CriteriosBusqueda  # noqa: E402
from tarjeta.modules.promociones.domain.promocion import Promocion  # noqa: E402
from tarjeta.modules.promociones.domain.vigencia import Vigencia  # noqa: E402
from tarjeta.modules.promociones.infrastructure.composition import (  # noqa: E402
    construir_puertos_promociones,
)
from tarjeta.modules.promociones.infrastructure.models import (  # noqa: E402
    PromocionModel,
    PromocionSucursalModel,
)
from tarjeta.shared.domain.types import EntityId  # noqa: E402


def _engine():
    return create_async_engine(str(get_settings().database_url))


@pytest.fixture
async def sm() -> AsyncIterator[async_sessionmaker]:
    eng = _engine()
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


async def _insertar_activa(
    sm: async_sessionmaker,
    *,
    id_sucursal: str,
    titulo: str = "Promo",
    valor_black: int = 20,
    valor_platino: int | None = 10,
    segmento: Segmento = Segmento.AMBOS,
    tope_total: int | None = None,
) -> str:
    async with sm() as s:
        promo = Promocion.crear(
            id_comercio=EntityId.new(),
            titulo=titulo,
            descripcion="",
            mecanica=Mecanica.PORCENTAJE,
            segmento=segmento,
            valor_platino=valor_platino,
            valor_black=valor_black,
            vigencia=_vig(),
            sucursales=[EntityId.from_str(id_sucursal)],
            tope_total=tope_total,
        )
        promo.activar()  # BORRADOR -> ACTIVA
        await construir_puertos_promociones(s).promociones.agregar(promo)
        await s.commit()
        return str(promo.id)


# --------------------------------------------------------------- concurrencia (§07.3)


async def test_concurrencia_sobre_tope_otorga_exactamente_M(sm: async_sessionmaker) -> None:
    M, N = 50, 200
    suc = str(uuid.uuid4())
    pid = await _insertar_activa(sm, id_sucursal=suc, tope_total=M)

    async def reservar() -> bool:
        async with sm() as s:
            try:
                await ReservarUso(construir_puertos_promociones(s)).ejecutar(id_promocion=pid)
                return True
            except TopeAgotado:
                return False

    resultados = await asyncio.gather(*(reservar() for _ in range(N)))
    otorgados = sum(1 for r in resultados if r)
    assert otorgados == M, f"esperados {M}, otorgados {otorgados}"

    # El contador final es exactamente M y quedó AGOTADA.
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None
        assert promo.usos_totales == M
        assert promo.estado.value == "AGOTADA"


# --------------------------------------------------------------- motor de resolución (§07.4)


async def test_platino_no_resuelve_exclusiva_black(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    await _insertar_activa(
        sm, id_sucursal=suc, segmento=Segmento.SOLO_BLACK, valor_platino=None, valor_black=30
    )
    ahora = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    async with sm() as s:
        motor = MotorResolucion(construir_puertos_promociones(s))
        para_platino = await motor.resolver(nivel="PLATINO", id_sucursal=suc, momento_local=ahora)
        para_black = await motor.resolver(nivel="BLACK", id_sucursal=suc, momento_local=ahora)
    assert para_platino == []
    assert len(para_black) == 1


async def test_conflicto_elige_mayor_beneficio(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    await _insertar_activa(sm, id_sucursal=suc, titulo="Chica", valor_black=10, valor_platino=10)
    await _insertar_activa(sm, id_sucursal=suc, titulo="Grande", valor_black=40, valor_platino=40)
    ahora = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    async with sm() as s:
        ordenadas = await MotorResolucion(construir_puertos_promociones(s)).resolver(
            nivel="BLACK", id_sucursal=suc, momento_local=ahora
        )
    assert [p.titulo for p in ordenadas][0] == "Grande"  # mayor beneficio primero


async def test_rendimiento_motor_volumen_realista(sm: async_sessionmaker) -> None:
    # Volumen realista: miles de promociones repartidas en cientos de sucursales.
    n_promos, n_suc = 3000, 300
    sucursales = [uuid.uuid4() for _ in range(n_suc)]
    target = sucursales[0]
    ahora = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    promo_rows = []
    link_rows = []
    for i in range(n_promos):
        pid = uuid.uuid4()
        promo_rows.append(
            {
                "id": pid,
                "id_comercio": uuid.uuid4(),
                "titulo": f"Promo {i}",
                "descripcion": "descripción de prueba",
                "mecanica": "PORCENTAJE",
                "segmento": "AMBOS",
                "valor_platino": 10,
                "valor_black": 10 + (i % 40),
                "fecha_desde": date(2026, 1, 1),
                "fecha_hasta": date(2027, 12, 31),
                "dias_semana": [],
                "hora_desde": None,
                "hora_hasta": None,
                "acumulable": False,
                "destacada_municipal": False,
                "tope_total": None,
                "tope_por_usuario": None,
                "tope_por_dia": None,
                "usos_totales": 0,
                "monto_minimo": 0,
                "imagen_url": "",
                "estado": "ACTIVA",
                "creada_en": datetime.now(UTC),
            }
        )
        link_rows.append({"id_promocion": pid, "id_sucursal": sucursales[i % n_suc]})

    async with sm() as s:
        await s.execute(insert(PromocionModel), promo_rows)
        await s.execute(insert(PromocionSucursalModel), link_rows)
        await s.commit()

    async with sm() as s:
        motor = MotorResolucion(construir_puertos_promociones(s))
        inicio = _time.perf_counter()
        resultado = await motor.resolver(
            nivel="BLACK", id_sucursal=str(target), momento_local=ahora
        )
        transcurrido = _time.perf_counter() - inicio

    print(f"\n[motor] {n_promos} promos / {n_suc} sucursales -> {transcurrido * 1000:.1f} ms")
    assert resultado, "el motor debería encontrar promociones de la sucursal objetivo"
    assert transcurrido < 0.5, f"motor demasiado lento: {transcurrido:.3f}s"


# --------------------------------------------------------------- búsqueda sin tildes (§07.6)


async def test_busqueda_sin_tildes(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    await _insertar_activa(sm, id_sucursal=suc, titulo="Panadería Ñoño con descripción")
    async with sm() as s:
        desc = construir_puertos_promociones(s)
        con = await desc.promociones.buscar(CriteriosBusqueda(texto="panaderia"))
        con_tilde = await desc.promociones.buscar(CriteriosBusqueda(texto="panadería"))
    titulos = {p.titulo for p in con}
    assert any("Panadería" in t for t in titulos)  # sin tildes encuentra con tildes
    assert con_tilde  # y con tildes también


# --------------------------------------------------------------- feed exclusivas black


async def test_feed_exclusivas_black(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    marca = f"Black-{uuid.uuid4().hex[:8]}"
    await _insertar_activa(
        sm,
        id_sucursal=suc,
        titulo=marca,
        segmento=Segmento.SOLO_BLACK,
        valor_platino=None,
        valor_black=50,
    )
    async with sm() as s:
        exclusivas = await construir_puertos_promociones(s).promociones.exclusivas_black(100)
    assert any(p.titulo == marca for p in exclusivas)


# --------------------------------------------------------------- deuda 07.0.B (ubicación única)


async def test_ubicacion_una_sola_fuente(sm: async_sessionmaker) -> None:
    # Se inserta una sucursal por SQL con solo `ubicacion`; el trigger deriva lat/lon.
    sid = uuid.uuid4()
    async with sm() as s:
        await s.execute(
            text(
                "INSERT INTO sucursal (id, id_comercio, nombre, direccion, telefono, ubicacion, "
                "estado, es_casa_central, horarios, fotos, qr_token, motivo_cierre) VALUES "
                "(:id, :com, 'S', '', '', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, "
                "'ACTIVA', false, '[]'::jsonb, '[]'::jsonb, '', '')"
            ),
            {"id": sid, "com": uuid.uuid4(), "lat": -31.53, "lon": -68.40},
        )
        await s.commit()
        fila = (
            await s.execute(text("SELECT lat, lon FROM sucursal WHERE id = :id"), {"id": sid})
        ).one()
    assert abs(fila.lat - (-31.53)) < 1e-6
    assert abs(fila.lon - (-68.40)) < 1e-6

    # Al mover SOLO la ubicación, lat/lon quedan coherentes por el trigger.
    async with sm() as s:
        await s.execute(
            text(
                "UPDATE sucursal SET ubicacion = "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography WHERE id = :id"
            ),
            {"id": sid, "lat": -32.0, "lon": -69.0},
        )
        await s.commit()
        fila = (
            await s.execute(text("SELECT lat, lon FROM sucursal WHERE id = :id"), {"id": sid})
        ).one()
    assert abs(fila.lat - (-32.0)) < 1e-6
    assert abs(fila.lon - (-69.0)) < 1e-6


# --------------------------------------------------------------- gestión + publicación + moderación


def _vig_dict() -> Vigencia:
    return Vigencia(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2027, 12, 31))


async def _crear_borrador(
    sm: async_sessionmaker, *, id_comercio: str, suc: str, titulo: str
) -> str:
    async with sm() as s:
        return await GestionPromociones(construir_puertos_promociones(s)).crear(
            id_comercio=id_comercio,
            titulo=titulo,
            descripcion="desc",
            mecanica=Mecanica.PORCENTAJE,
            segmento=Segmento.AMBOS,
            valor_platino=10,
            valor_black=20,
            vigencia=_vig_dict(),
            sucursales=[suc],
            tope_total=100,
        )


async def test_gestion_publicacion_moderacion_flujo(sm: async_sessionmaker) -> None:
    com = str(uuid.uuid4())
    suc = str(uuid.uuid4())
    pid = await _crear_borrador(sm, id_comercio=com, suc=suc, titulo="Promo A")

    # Editar condiciones en BORRADOR.
    async with sm() as s:
        await GestionPromociones(construir_puertos_promociones(s)).editar_condiciones(
            id_promocion=pid,
            id_comercio=com,
            mecanica=Mecanica.PORCENTAJE,
            valor_platino=15,
            valor_black=25,
            tope_total=50,
        )

    # Comercio NUEVO: publicar => va a EN_REVISION.
    async with sm() as s:
        estado = await PublicarPromocion(construir_puertos_promociones(s)).ejecutar(
            id_promocion=pid, id_comercio=com, umbral_establecido=3, umbral_verificado=10
        )
    assert estado == "EN_REVISION"

    # En la cola de moderación.
    async with sm() as s:
        cola = await construir_puertos_promociones(s).promociones.listar_en_revision()
    assert any(str(p.id) == pid for p in cola)

    # Moderar: aprobar => ACTIVA + suma confianza.
    async with sm() as s:
        await ModerarPromocion(construir_puertos_promociones(s)).aprobar(
            id_promocion=pid, umbral_establecido=3, umbral_verificado=10
        )
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.estado.value == "ACTIVA"

    # Pausar / reanudar / duplicar.
    async with sm() as s:
        g = GestionPromociones(construir_puertos_promociones(s))
        await g.pausar(id_promocion=pid, id_comercio=com)
    async with sm() as s:
        g = GestionPromociones(construir_puertos_promociones(s))
        await g.reanudar(id_promocion=pid, id_comercio=com)
    async with sm() as s:
        copia = await GestionPromociones(construir_puertos_promociones(s)).duplicar(
            id_promocion=pid, id_comercio=com
        )
    assert copia != pid


async def test_confianza_auto_publica_tras_umbral(sm: async_sessionmaker) -> None:
    com = str(uuid.uuid4())
    suc = str(uuid.uuid4())
    # Aprobar 3 promos => el comercio pasa a ESTABLECIDO.
    for i in range(3):
        pid = await _crear_borrador(sm, id_comercio=com, suc=suc, titulo=f"P{i}")
        async with sm() as s:
            await PublicarPromocion(construir_puertos_promociones(s)).ejecutar(
                id_promocion=pid, id_comercio=com, umbral_establecido=3, umbral_verificado=10
            )
        async with sm() as s:
            await ModerarPromocion(construir_puertos_promociones(s)).aprobar(
                id_promocion=pid, umbral_establecido=3, umbral_verificado=10
            )
    # La 4a se auto-publica (ESTABLECIDO no requiere revisión previa).
    pid4 = await _crear_borrador(sm, id_comercio=com, suc=suc, titulo="P4")
    async with sm() as s:
        estado = await PublicarPromocion(construir_puertos_promociones(s)).ejecutar(
            id_promocion=pid4, id_comercio=com, umbral_establecido=3, umbral_verificado=10
        )
    assert estado == "ACTIVA"


async def test_moderar_rechazar_y_aprobar_con_edicion(sm: async_sessionmaker) -> None:
    com = str(uuid.uuid4())
    suc = str(uuid.uuid4())
    pid = await _crear_borrador(sm, id_comercio=com, suc=suc, titulo="A rechazar")
    async with sm() as s:
        await PublicarPromocion(construir_puertos_promociones(s)).ejecutar(
            id_promocion=pid, id_comercio=com, umbral_establecido=3, umbral_verificado=10
        )
    async with sm() as s:
        await ModerarPromocion(construir_puertos_promociones(s)).rechazar(
            id_promocion=pid, motivo="imagen incoherente"
        )
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid))
        assert promo is not None and promo.estado.value == "RECHAZADA"

    # Aprobar con edición sobre otra promo.
    pid2 = await _crear_borrador(sm, id_comercio=com, suc=suc, titulo="Editar al aprobar")
    async with sm() as s:
        await PublicarPromocion(construir_puertos_promociones(s)).ejecutar(
            id_promocion=pid2, id_comercio=com, umbral_establecido=3, umbral_verificado=10
        )
    async with sm() as s:
        await ModerarPromocion(construir_puertos_promociones(s)).aprobar_con_edicion(
            id_promocion=pid2,
            titulo="Título corregido",
            descripcion="d",
            imagen_url="u",
            umbral_establecido=3,
            umbral_verificado=10,
        )
    async with sm() as s:
        promo = await construir_puertos_promociones(s).promociones.obtener(EntityId.from_str(pid2))
        assert promo is not None and promo.titulo == "Título corregido"
        assert promo.estado.value == "ACTIVA"


# --------------------------------------------------------------- descubrimiento + proponer


async def test_descubrimiento_feed_favoritos_y_listado(sm: async_sessionmaker) -> None:
    com = str(uuid.uuid4())
    suc = str(uuid.uuid4())
    await _insertar_activa(sm, id_sucursal=suc, titulo="Nueva de la semana")
    async with sm() as s:
        desc = Descubrimiento(construir_puertos_promociones(s))
        nuevas = await desc.nuevas_esta_semana()
        vencen = await desc.vencen_pronto(dias=3650)  # ventana amplia => incluye las de prueba
        exclusivas = await desc.exclusivas_black()
    assert nuevas  # hay al menos una creada recién
    assert isinstance(vencen, list)
    assert isinstance(exclusivas, list)

    # Favoritos: marcar, listar, quitar.
    persona = str(uuid.uuid4())
    async with sm() as s:
        d = Descubrimiento(construir_puertos_promociones(s))
        await d.marcar_favorito(id_persona=persona, comercio=com, rubro="kiosco")
    async with sm() as s:
        favs = await Descubrimiento(construir_puertos_promociones(s)).favoritos_de(
            id_persona=persona
        )
    assert com in favs["comercios"] and "kiosco" in favs["rubros"]
    async with sm() as s:
        await Descubrimiento(construir_puertos_promociones(s)).quitar_favorito(
            id_persona=persona, comercio=com
        )
    async with sm() as s:
        favs = await Descubrimiento(construir_puertos_promociones(s)).favoritos_de(
            id_persona=persona
        )
    assert com not in favs["comercios"]

    # listar_por_comercio + búsqueda restringida a sucursales.
    await _insertar_activa(sm, id_sucursal=suc, titulo="En mi sucursal")
    async with sm() as s:
        acotada = await construir_puertos_promociones(s).promociones.buscar(
            CriteriosBusqueda(texto="sucursal", ids_sucursal=[suc])
        )
    assert any("sucursal" in p.titulo.lower() for p in acotada)


async def test_proponer_incluye_acumulables(sm: async_sessionmaker) -> None:
    suc = str(uuid.uuid4())
    # Una no acumulable de mayor beneficio + una acumulable.
    async with sm() as s:
        g = construir_puertos_promociones(s)
        base = Promocion.crear(
            id_comercio=EntityId.new(),
            titulo="Base",
            descripcion="",
            mecanica=Mecanica.PORCENTAJE,
            segmento=Segmento.AMBOS,
            valor_platino=40,
            valor_black=40,
            vigencia=_vig(),
            sucursales=[EntityId.from_str(suc)],
        )
        base.activar()
        await g.promociones.agregar(base)
        acum = Promocion.crear(
            id_comercio=EntityId.new(),
            titulo="Acumulable",
            descripcion="",
            mecanica=Mecanica.MULTIPLICADOR_PUNTOS,
            segmento=Segmento.AMBOS,
            valor_platino=200,
            valor_black=200,
            vigencia=_vig(),
            sucursales=[EntityId.from_str(suc)],
            acumulable=True,
        )
        acum.activar()
        await g.promociones.agregar(acum)
        await s.commit()
    ahora = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    async with sm() as s:
        propuestas = await MotorResolucion(construir_puertos_promociones(s)).proponer(
            nivel="BLACK", id_sucursal=suc, momento_local=ahora
        )
    titulos = [p.titulo for p in propuestas]
    assert "Acumulable" in titulos  # la acumulable siempre entra a la propuesta
