"""Integración: puntos — libro append-only, FIFO, circuito cerrado, anulación, vencimiento,
inventario, concurrencia y latencia de la reserva. Requiere PostgreSQL real.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.modules.puntos.application.canje import PuntosCanjeServicio  # noqa: E402
from tarjeta.modules.puntos.application.consulta import ConsultaBilleteras  # noqa: E402
from tarjeta.modules.puntos.application.contabilidad import Contabilidad  # noqa: E402
from tarjeta.modules.puntos.application.inventario import (  # noqa: E402
    CanjearInventario,
    GestionInventario,
)
from tarjeta.modules.puntos.application.municipales import AcreditarPuntosMunicipales  # noqa: E402
from tarjeta.modules.puntos.application.vencimiento import VencerLotes  # noqa: E402
from tarjeta.modules.puntos.domain.errors import SaldoInsuficiente, StockAgotado  # noqa: E402
from tarjeta.modules.puntos.domain.moneda import TipoMoneda, TipoTitular  # noqa: E402
from tarjeta.modules.puntos.infrastructure.composition import (  # noqa: E402
    construir_puertos_puntos,
)


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


def _p(session):  # type: ignore[no-untyped-def]
    return construir_puertos_puntos(session)


async def _acreditar(sm, persona, comercio, puntos, *, vence_en=None, tx=None, clave=None):  # type: ignore[no-untyped-def]
    async with sm() as s:
        n = await Contabilidad(_p(s)).acreditar(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=puntos,
            concepto="test",
            vence_en=vence_en,
            id_transaccion=tx,
            clave_dedup=clave,
        )
        await s.commit()
        return n


async def _saldo_pc(sm, persona, comercio) -> int:  # type: ignore[no-untyped-def]
    async with sm() as s:
        b = await _p(s).billeteras.obtener(
            tipo_titular=TipoTitular.PERSONA,
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
        return b.saldo if b else 0


# --------------------------------------------------------------- libro inmutable


async def test_libro_append_only_a_nivel_db(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio, 100)
    eng = create_async_engine(str(get_settings().database_url))  # rol tarjeta_app
    try:
        with pytest.raises(Exception) as exc_update:
            async with eng.begin() as c:
                await c.execute(text("UPDATE movimiento_billetera SET monto = 0"))
        assert "permission denied" in str(exc_update.value).lower()
        with pytest.raises(Exception) as exc_delete:
            async with eng.begin() as c:
                await c.execute(text("DELETE FROM movimiento_billetera"))
        assert "permission denied" in str(exc_delete.value).lower()
    finally:
        await eng.dispose()


async def test_saldo_coincide_con_suma_de_movimientos(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio, 100)
    async with sm() as s:
        await Contabilidad(_p(s)).consumir(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=30,
            concepto="consumo",
        )
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 70
    async with sm() as s:
        assert await ConsultaBilleteras(_p(s)).verificar_consistencia(persona) is True


# --------------------------------------------------------------- FIFO por vencimiento


async def test_consumo_fifo_respeta_orden_de_vencimiento(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    hoy = datetime.now(UTC).date()
    # Lote que vence ANTES (aunque se crea después) debe consumirse primero.
    await _acreditar(sm, persona, comercio, 50, vence_en=hoy + timedelta(days=90))
    await _acreditar(sm, persona, comercio, 50, vence_en=hoy + timedelta(days=10))
    async with sm() as s:
        consumido = await Contabilidad(_p(s)).consumir(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=60,
            concepto="fifo",
        )
        await s.commit()
    assert consumido == 60
    async with sm() as s:
        b = await _p(s).billeteras.obtener(
            tipo_titular=TipoTitular.PERSONA,
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
        lotes = await _p(s).lotes.disponibles_fifo(b.id, hoy)  # type: ignore[union-attr]
    # El lote que vence en 10 días quedó en 0; el de 90 días conserva 40.
    por_venc = {lote.vence_en: lote.saldo_restante for lote in lotes}
    assert por_venc.get(hoy + timedelta(days=90)) == 40
    assert (hoy + timedelta(days=10)) not in por_venc  # consumido por completo


# --------------------------------------------------------------- circuito cerrado por comercio


async def test_pc_de_un_comercio_no_se_gastan_en_otro(sm: async_sessionmaker) -> None:
    persona = str(uuid.uuid4())
    comercio_a, comercio_b = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio_a, 100)
    # En el comercio B no hay saldo: no se puede consumir.
    async with sm() as s:
        with pytest.raises(SaldoInsuficiente):
            await Contabilidad(_p(s)).consumir(
                id_titular=persona,
                tipo_moneda=TipoMoneda.PC,
                id_comercio=comercio_b,
                puntos=10,
                concepto="cruzado",
            )
    assert await _saldo_pc(sm, persona, comercio_a) == 100  # intacto
    assert await _saldo_pc(sm, persona, comercio_b) == 0


async def test_pc_y_pm_no_se_convierten(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio, 100)  # PC
    async with sm() as s:
        await Contabilidad(_p(s)).acreditar(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
            puntos=50,
            concepto="pm",
        )
        await s.commit()
    # Consumir PC no toca PM y viceversa; son libros separados.
    async with sm() as s:
        await Contabilidad(_p(s)).consumir(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=100,
            concepto="gasto pc",
        )
        await s.commit()
    async with sm() as s:
        r = await ConsultaBilleteras(_p(s)).resumen(persona)
    assert r.pm == 50  # PM intacto
    assert dict((x.id_comercio, x.saldo) for x in r.pc)[comercio] == 0


# --------------------------------------------------------------- anulación / compensatorio


async def test_anulacion_revierte_con_compensatorio_sin_editar_original(
    sm: async_sessionmaker,
) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    tx = str(uuid.uuid4())
    async with sm() as s:
        await PuntosCanjeServicio(_p(s)).acreditar_canje(
            id_transaccion=tx,
            id_titular=persona,
            id_comercio=comercio,
            mecanica="MULTIPLICADOR_PUNTOS",
            valor=2,
            monto=1000,
        )
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 20
    async with sm() as s:
        await PuntosCanjeServicio(_p(s)).revertir_canje(id_transaccion=tx)
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 0
    async with sm() as s:
        movs = await _p(s).movimientos.por_transaccion(tx)
    tipos = sorted(m.tipo.value for m in movs)
    assert "ACREDITACION" in tipos  # el original sigue existiendo
    assert "REVERSA_ACREDITACION" in tipos  # y hay un compensatorio


async def test_anulacion_con_puntos_ya_gastados_deja_saldo_negativo(
    sm: async_sessionmaker,
) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    tx = str(uuid.uuid4())
    async with sm() as s:
        await PuntosCanjeServicio(_p(s)).acreditar_canje(
            id_transaccion=tx,
            id_titular=persona,
            id_comercio=comercio,
            mecanica="MULTIPLICADOR_PUNTOS",
            valor=2,
            monto=1000,
        )
        await s.commit()
    # El vecino gasta esos 20 puntos en otra compra del mismo comercio.
    async with sm() as s:
        await Contabilidad(_p(s)).consumir(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=20,
            concepto="gasto",
        )
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 0
    # Se anula el canje original: como ya se gastaron, el saldo queda en negativo (definido).
    async with sm() as s:
        await PuntosCanjeServicio(_p(s)).revertir_canje(id_transaccion=tx)
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == -20
    async with sm() as s:
        assert await ConsultaBilleteras(_p(s)).verificar_consistencia(persona) is True


async def test_consumo_en_canje_y_reversa_restituye(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio, 100)
    tx = str(uuid.uuid4())
    # El ciudadano usa 10 puntos en la operación (tope de 1000 pesos, valor punto 1).
    async with sm() as s:
        consumido, pesos = await PuntosCanjeServicio(_p(s)).consumir_canje(
            id_transaccion=tx,
            id_titular=persona,
            id_comercio=comercio,
            puntos_solicitados=10,
            tope_pesos=1000,
        )
        await s.commit()
    assert (consumido, pesos) == (10, 10)
    assert await _saldo_pc(sm, persona, comercio) == 90
    # tope de 0 pesos no consume nada.
    async with sm() as s:
        assert await PuntosCanjeServicio(_p(s)).consumir_canje(
            id_transaccion=str(uuid.uuid4()),
            id_titular=persona,
            id_comercio=comercio,
            puntos_solicitados=10,
            tope_pesos=0,
        ) == (0, 0)
    # Anular la operación restituye los puntos consumidos (compensatorio REVERSA_CONSUMO).
    async with sm() as s:
        await PuntosCanjeServicio(_p(s)).revertir_canje(id_transaccion=tx)
        await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 100
    async with sm() as s:
        movs = await _p(s).movimientos.por_transaccion(tx)
    assert any(m.tipo.value == "REVERSA_CONSUMO" for m in movs)


async def test_pasivo_comercio_y_pm_en_circulacion(sm: async_sessionmaker) -> None:
    comercio = str(uuid.uuid4())
    p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
    # PC emitidos por el comercio a dos vecinos, y un consumo.
    await _acreditar(sm, p1, comercio, 100)
    await _acreditar(sm, p2, comercio, 40)
    async with sm() as s:
        await Contabilidad(_p(s)).consumir(
            id_titular=p1,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=30,
            concepto="gasto",
        )
        await s.commit()
    async with sm() as s:
        emitidos, canjeados = await _p(s).movimientos.resumen_comercio(comercio)
    assert emitidos == 140 and canjeados == 30
    # PM en circulación = suma de saldos de billeteras PM.
    async with sm() as s:
        await Contabilidad(_p(s)).acreditar(
            id_titular=p1, tipo_moneda=TipoMoneda.PM, id_comercio=None, puntos=25, concepto="pm"
        )
        await s.commit()
    async with sm() as s:
        total = await _p(s).movimientos.pm_en_circulacion()
    assert total >= 25


# --------------------------------------------------------------- idempotencia


async def test_reintento_no_acredita_dos_veces(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    tx = str(uuid.uuid4())
    for _ in range(2):
        async with sm() as s:
            await PuntosCanjeServicio(_p(s)).acreditar_canje(
                id_transaccion=tx,
                id_titular=persona,
                id_comercio=comercio,
                mecanica="MULTIPLICADOR_PUNTOS",
                valor=2,
                monto=1000,
            )
            await s.commit()
    assert await _saldo_pc(sm, persona, comercio) == 20  # una sola vez


# --------------------------------------------------------------- concurrencia de consumo


async def test_concurrencia_consumo_no_deja_saldo_imposible(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    await _acreditar(sm, persona, comercio, 100)

    async def gastar_30() -> bool:
        async with sm() as s:
            try:
                await Contabilidad(_p(s)).consumir(
                    id_titular=persona,
                    tipo_moneda=TipoMoneda.PC,
                    id_comercio=comercio,
                    puntos=30,
                    concepto="conc",
                )
                await s.commit()
                return True
            except SaldoInsuficiente:
                return False

    exitos = sum(await asyncio.gather(*(gastar_30() for _ in range(10))))
    assert exitos == 3  # 3 * 30 = 90 <= 100; el 4º no entra
    assert await _saldo_pc(sm, persona, comercio) == 10
    async with sm() as s:
        assert await ConsultaBilleteras(_p(s)).verificar_consistencia(persona) is True


# --------------------------------------------------------------- vencimiento idempotente


async def test_vencimiento_idempotente(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    ayer = datetime.now(UTC).date() - timedelta(days=1)
    await _acreditar(sm, persona, comercio, 100, vence_en=ayer)
    async with sm() as s:
        n1 = await VencerLotes(_p(s)).ejecutar()
    assert n1 >= 1
    assert await _saldo_pc(sm, persona, comercio) == 0
    async with sm() as s:
        n2 = await VencerLotes(_p(s)).ejecutar()
    assert n2 == 0  # correrlo de nuevo no vence dos veces
    assert await _saldo_pc(sm, persona, comercio) == 0
    # Un solo movimiento de vencimiento en el libro de esa billetera.
    async with sm() as s:
        b = await _p(s).billeteras.obtener(
            tipo_titular=TipoTitular.PERSONA,
            id_titular=persona,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
        movs = await _p(s).movimientos.listar(b.id, 100)  # type: ignore[union-attr]
    assert sum(1 for m in movs if m.tipo.value == "VENCIMIENTO") == 1


# --------------------------------------------------------------- inventario municipal


async def test_inventario_reserva_cupo_bajo_concurrencia(sm: async_sessionmaker) -> None:
    persona = str(uuid.uuid4())
    hoy = datetime.now(UTC).date()
    async with sm() as s:
        await Contabilidad(_p(s)).acreditar(
            id_titular=persona,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
            puntos=100,
            concepto="pm",
        )
        await s.commit()
    async with sm() as s:
        id_item = await GestionInventario(_p(s)).publicar(
            titulo="Entrada",
            descripcion="",
            costo_pm=10,
            stock=5,
            fecha_desde=hoy,
            fecha_hasta=hoy + timedelta(days=30),
        )

    async def canjear() -> bool:
        async with sm() as s:
            try:
                await CanjearInventario(_p(s)).ejecutar(id_persona=persona, id_item=id_item)
                return True
            except StockAgotado, SaldoInsuficiente:
                return False

    exitos = sum(await asyncio.gather(*(canjear() for _ in range(10))))
    assert exitos == 5  # stock limita a 5 aunque haya PM para 10
    async with sm() as s:
        comps = await CanjearInventario(_p(s)).comprobantes_de(persona)
    assert len(comps) == 5
    async with sm() as s:
        r = await ConsultaBilleteras(_p(s)).resumen(persona)
    assert r.pm == 50  # 100 - 5*10


async def test_inventario_sin_saldo_no_entrega(sm: async_sessionmaker) -> None:
    persona = str(uuid.uuid4())
    hoy = datetime.now(UTC).date()
    async with sm() as s:
        id_item = await GestionInventario(_p(s)).publicar(
            titulo="Taller",
            descripcion="",
            costo_pm=1000,
            stock=3,
            fecha_desde=hoy,
            fecha_hasta=hoy + timedelta(days=30),
        )
    async with sm() as s:
        with pytest.raises(SaldoInsuficiente):
            await CanjearInventario(_p(s)).ejecutar(id_persona=persona, id_item=id_item)
    # El stock no se descontó porque la transacción se revirtió por completo.
    async with sm() as s:
        from tarjeta.shared.domain.types import EntityId

        item = await _p(s).catalogo.obtener(EntityId.from_str(id_item))
    assert item is not None and item.stock == 3


# --------------------------------------------------------------- PM por estar al día


def _p_pm(session):  # type: ignore[no-untyped-def]
    # Puertos con la generación de PM encendida (§10.0.B: apagada por defecto).
    from tarjeta.modules.puntos.application.deps import PuntosConfig

    return construir_puertos_puntos(session, PuntosConfig(generacion_pm_activa=True))


async def test_pm_por_estar_al_dia_es_idempotente_por_periodo(sm: async_sessionmaker) -> None:
    persona = str(uuid.uuid4())
    async with sm() as s:
        n1 = await AcreditarPuntosMunicipales(_p_pm(s)).por_estar_al_dia(
            id_persona=persona, periodo="2026-09"
        )
    async with sm() as s:
        n2 = await AcreditarPuntosMunicipales(_p_pm(s)).por_estar_al_dia(
            id_persona=persona, periodo="2026-09"
        )
    async with sm() as s:
        n3 = await AcreditarPuntosMunicipales(_p_pm(s)).por_estar_al_dia(
            id_persona=persona, periodo="2026-10"
        )
    assert n1 == 50 and n2 == 0 and n3 == 50  # una vez por período


async def test_pm_no_se_genera_con_la_flag_apagada(sm: async_sessionmaker) -> None:
    # §10.0.B: con la generación de PM apagada (default), estar al día no acredita nada.
    persona = str(uuid.uuid4())
    async with sm() as s:
        n = await AcreditarPuntosMunicipales(_p(s)).por_estar_al_dia(
            id_persona=persona, periodo="2026-09"
        )
    assert n == 0


# --------------------------------------------------------------- feature flag canje contra tasas


async def test_canje_contra_tasas_apagado_sin_camino_expuesto() -> None:
    from tarjeta.main import create_app

    assert get_settings().ff_canje_contra_tasas is False
    app = create_app()
    import json

    blob = json.dumps(app.openapi()).lower()
    assert "tasa" not in blob  # ningún endpoint expone el canje contra tasas


# --------------------------------------------------------------- consulta (lecturas)


async def test_consulta_movimientos_y_por_vencer(sm: async_sessionmaker) -> None:
    persona, comercio = str(uuid.uuid4()), str(uuid.uuid4())
    hoy = datetime.now(UTC).date()
    await _acreditar(sm, persona, comercio, 100, vence_en=hoy + timedelta(days=5))
    async with sm() as s:
        movs = await ConsultaBilleteras(_p(s)).movimientos(
            persona, tipo_moneda="PC", id_comercio=comercio
        )
        por_vencer = await ConsultaBilleteras(_p(s)).por_vencer(persona, dias=30)
    assert len(movs) == 1 and movs[0].tipo.value == "ACREDITACION"
    assert any(x.dias_restantes <= 7 for x in por_vencer)  # aviso a 7 días visible


# --------------------------------------------------------------- deuda §09.0.A: latencia


async def test_latencia_reserva_bajo_contencion(sm: async_sessionmaker) -> None:
    """Mide la latencia de la reserva de tope con contención sostenida (§09.0.A)."""
    from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento
    from tarjeta.modules.promociones.domain.promocion import Promocion
    from tarjeta.modules.promociones.domain.vigencia import Vigencia
    from tarjeta.modules.promociones.infrastructure.composition import (
        construir_puertos_promociones,
    )
    from tarjeta.shared.domain.types import EntityId

    suc = EntityId.new()
    async with sm() as s:
        promo = Promocion.crear(
            id_comercio=EntityId.new(),
            titulo="Contención",
            descripcion="",
            mecanica=Mecanica.PORCENTAJE,
            segmento=Segmento.AMBOS,
            valor_platino=10,
            valor_black=20,
            vigencia=Vigencia(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2027, 12, 31)),
            sucursales=[suc],
            tope_total=10_000,
        )
        promo.activar()
        await construir_puertos_promociones(s).promociones.agregar(promo)
        await s.commit()
        pid = str(promo.id)

    hoy = datetime.now(UTC).date()
    N = 50
    latencias: list[float] = []

    async def reservar() -> None:
        persona = str(uuid.uuid4())
        async with sm() as s:
            repo = construir_puertos_promociones(s).promociones
            t0 = time.perf_counter()
            await repo.reservar_uso(EntityId.from_str(pid), EntityId.from_str(persona), hoy)
            await s.commit()
            latencias.append((time.perf_counter() - t0) * 1000)

    await asyncio.gather(*(reservar() for _ in range(N)))
    latencias.sort()
    p95 = latencias[int(len(latencias) * 0.95) - 1]
    print(f"\n[latencia reserva contención] N={N} p50={latencias[N // 2]:.1f}ms p95={p95:.1f}ms")
    # Umbral generoso para una caja; si se supera hay que optimizar (se informa el número).
    assert p95 < 2000, f"p95 {p95:.1f}ms supera el umbral de una caja"
