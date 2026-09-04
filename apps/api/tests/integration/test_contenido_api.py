"""Integración: contenido — cuota atómica, devolución ante error, superposición del %,
metadato de IA, moderación por confianza, editor sin crédito. Requiere PostgreSQL real.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from io import BytesIO

import pytest

pytestmark = pytest.mark.integration

from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.modules.contenido.application.deps import (  # noqa: E402
    ContenidoConfig,
    ContenidoPuertos,
)
from tarjeta.modules.contenido.application.generacion import (  # noqa: E402
    CrearPiezaDesdeFoto,
    EditarPieza,
    GenerarPieza,
    RegenerarSuperposicion,
)
from tarjeta.modules.contenido.application.moderacion import ModeracionPiezas  # noqa: E402
from tarjeta.modules.contenido.domain.errors import (  # noqa: E402
    CuotaAgotada,
    GeneracionFallida,
    ProveedorNoConfigurado,
    TransicionPiezaInvalida,
)
from tarjeta.modules.contenido.domain.pieza import Superposicion  # noqa: E402
from tarjeta.modules.contenido.domain.tipos import EstadoPieza  # noqa: E402
from tarjeta.modules.contenido.infrastructure.almacen import AlmacenLocal  # noqa: E402
from tarjeta.modules.contenido.infrastructure.compositor import CompositorPIL  # noqa: E402
from tarjeta.modules.contenido.infrastructure.generador import (  # noqa: E402
    GeneradorReal,
    GeneradorSimulacion,
)
from tarjeta.modules.contenido.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyCreditoRepository,
    SqlAlchemyPiezaRepository,
)
from tarjeta.orquestacion import build_dispatcher  # noqa: E402
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork  # noqa: E402
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox  # noqa: E402

PERIODO = "2026-09"
_dispatcher = build_dispatcher(get_settings())


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


@pytest.fixture
def almacen(tmp_path) -> AlmacenLocal:  # type: ignore[no-untyped-def]
    return AlmacenLocal(str(tmp_path))


@pytest.fixture(autouse=True)
async def _drenar_outbox(sm: async_sessionmaker) -> AsyncIterator[None]:
    # Estas piezas escriben eventos al outbox compartido; se drenan al terminar para no dejar
    # una cola vieja que retrase el procesamiento de otros tests (p. ej. el flujo HTTP del canje).
    yield
    for _ in range(10):
        async with sm() as s:
            if await _dispatcher.drain(s) == 0:
                break


class _GeneradorRoto:
    nombre = "roto"

    async def generar(self, prompt: str, *, cantidad: int, tamano: str) -> list[bytes]:
        raise RuntimeError("el proveedor explotó")


def _puertos(session, almacen, *, generador=None, variantes=4):  # type: ignore[no-untyped-def]
    return ContenidoPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        piezas=SqlAlchemyPiezaRepository(session),
        creditos=SqlAlchemyCreditoRepository(session),
        generador=generador or GeneradorSimulacion(),
        compositor=CompositorPIL(),
        almacen=almacen,
        outbox=SqlAlchemyOutbox(session),
        config=ContenidoConfig(
            cuota_mensual=10, variantes_por_credito=variantes, modelo="simulacion"
        ),
    )


def _superpos(porcentaje: str = "20%") -> Superposicion:
    return Superposicion(porcentaje=porcentaje, vigencia="Hasta 2026-12-31", nombre="La Nona")


async def _generar(sm, almacen, *, comercio, auto=True, generador=None, idea="empanadas"):  # type: ignore[no-untyped-def]
    async with sm() as s:
        return await GenerarPieza(_puertos(s, almacen, generador=generador)).ejecutar(
            id_comercio=comercio,
            id_promocion=str(uuid.uuid4()),
            idea=idea,
            rubro="gastronomía",
            nombre_fantasia="La Nona",
            mecanica="PORCENTAJE",
            estilo_plantilla="clasica",
            superposicion=_superpos(),
            plantilla="clasica",
            auto_aprueba=auto,
            periodo=PERIODO,
        )


async def _usados(sm, comercio) -> int:  # type: ignore[no-untyped-def]
    async with sm() as s:
        return await SqlAlchemyCreditoRepository(s).usados(comercio, PERIODO)


# --------------------------------------------------------------- proveedor


def test_simulacion_es_determinista_y_sin_red() -> None:
    gen = GeneradorSimulacion()

    async def run() -> None:
        a = await gen.generar("hola", cantidad=4, tamano="256x256")
        b = await gen.generar("hola", cantidad=4, tamano="256x256")
        assert len(a) == 4 and a == b  # deterministas
        assert a[0][:8] == b"\x89PNG\r\n\x1a\n"  # PNG válido

    asyncio.run(run())


def test_adaptador_real_exige_configuracion() -> None:
    with pytest.raises(ProveedorNoConfigurado):
        GeneradorReal(api_key="", modelo="x", base_url="")


# --------------------------------------------------------------- cuota


async def test_reserva_credito_bajo_concurrencia(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())

    async def gen(i: int) -> bool:
        try:
            await _generar(sm, almacen, comercio=comercio, idea=f"idea {i}")
            return True
        except CuotaAgotada:
            return False

    exitos = sum(await asyncio.gather(*(gen(i) for i in range(15))))
    assert exitos == 10  # la cuota; dos pestañas no gastan el mismo crédito
    assert await _usados(sm, comercio) == 10


async def test_generacion_fallida_devuelve_el_credito(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    with pytest.raises(GeneracionFallida):
        await _generar(sm, almacen, comercio=comercio, generador=_GeneradorRoto())
    assert await _usados(sm, comercio) == 0  # reservado y devuelto


# --------------------------------------------------------------- superposición (§11.5)


async def test_pieza_muestra_el_porcentaje_de_la_promo(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio)
    assert pieza.superposicion.porcentaje == "20%"
    usados_antes = await _usados(sm, comercio)
    # Cambia el % de la promoción: se recompone la superposición SIN gastar crédito.
    async with sm() as s:
        pieza2 = await RegenerarSuperposicion(_puertos(s, almacen)).ejecutar(
            id_pieza=str(pieza.id), superposicion=_superpos("35%")
        )
    assert pieza2.superposicion.porcentaje == "35%"
    assert await _usados(sm, comercio) == usados_antes


async def test_toda_pieza_ia_lleva_metadato_de_origen(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio)
    assert pieza.generada_por_ia and pieza.modelo_ia == "simulacion"
    # El PNG derivado lleva el metadato de origen por IA.
    clave = next(iter(pieza.formatos.values()))
    datos = await almacen.leer(clave)
    assert datos is not None
    img = Image.open(BytesIO(datos))
    assert img.text.get("origen") == "IA"  # type: ignore[attr-defined]


# --------------------------------------------------------------- moderación (§11.6)


async def test_pieza_entra_a_moderacion_segun_confianza(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    en_cola = await _generar(sm, almacen, comercio=comercio, auto=False)  # comercio no verificado
    assert en_cola.estado is EstadoPieza.EN_MODERACION
    verificado = await _generar(sm, almacen, comercio=str(uuid.uuid4()), auto=True)
    assert verificado.estado is EstadoPieza.APROBADA


async def test_pieza_rechazada_no_se_puede_publicar(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio, auto=False)
    async with sm() as s:
        await ModeracionPiezas(_puertos(s, almacen)).rechazar(
            id_pieza=str(pieza.id), motivo="producto engañoso"
        )
    async with sm() as s:
        recargada = await _puertos(s, almacen).piezas.obtener(pieza.id)
    assert recargada is not None and recargada.estado is EstadoPieza.RECHAZADA
    assert recargada.publicable is False
    # No hay camino para aprobarla después de rechazada.
    async with sm() as s:
        with pytest.raises(TransicionPiezaInvalida):
            await ModeracionPiezas(_puertos(s, almacen)).aprobar(id_pieza=str(pieza.id))


# --------------------------------------------------------------- editor / foto propia


async def test_editor_produce_tres_formatos_sin_credito(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio)
    assert len(pieza.formatos) == 3
    usados_antes = await _usados(sm, comercio)
    async with sm() as s:
        editada = await EditarPieza(_puertos(s, almacen)).cambiar_plantilla(
            id_pieza=str(pieza.id), plantilla="fresca"
        )
    assert len(editada.formatos) == 3 and editada.plantilla == "fresca"
    assert await _usados(sm, comercio) == usados_antes  # el editor no gasta crédito


async def test_credito_extra_habilita_mas_generaciones(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    from tarjeta.modules.contenido.application.cuota import Creditos

    comercio = str(uuid.uuid4())
    for i in range(10):  # agota la cuota
        await _generar(sm, almacen, comercio=comercio, idea=f"idea {i}")
    with pytest.raises(CuotaAgotada):
        await _generar(sm, almacen, comercio=comercio)
    # El municipio otorga 2 créditos extra puntuales en campaña (§11.9).
    async with sm() as s:
        await Creditos(_puertos(s, almacen)).otorgar_extra(
            id_comercio=comercio, periodo=PERIODO, cantidad=2
        )
    await _generar(sm, almacen, comercio=comercio, idea="extra")  # ya no lanza
    async with sm() as s:
        est = await Creditos(_puertos(s, almacen)).estado(id_comercio=comercio, periodo=PERIODO)
    assert est.usados == 11 and est.disponibles == 1


async def test_elegir_variante_sin_credito(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio)  # 4 variantes
    usados_antes = await _usados(sm, comercio)
    async with sm() as s:
        editada = await EditarPieza(_puertos(s, almacen)).elegir_variante(
            id_pieza=str(pieza.id), indice=2
        )
    assert editada.imagen_fondo_clave == pieza.variantes_claves[2]
    assert await _usados(sm, comercio) == usados_antes  # elegir variante no gasta crédito


async def test_retencion_purga_objetos(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    from tarjeta.modules.contenido.application.retencion import Retencion

    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio)
    clave = next(iter(pieza.formatos.values()))
    assert await almacen.leer(clave) is not None
    async with sm() as s:
        await Retencion(_puertos(s, almacen)).purgar_pieza(id_pieza=str(pieza.id))
    assert await almacen.leer(clave) is None  # objetos liberados
    async with sm() as s:
        recargada = await _puertos(s, almacen).piezas.obtener(pieza.id)
    assert recargada is not None and recargada.formatos == {}  # queda la fila como registro


async def test_composition_arma_los_puertos(sm: async_sessionmaker) -> None:
    # El composition root arma generador (simulación por defecto), config y puertos.
    from tarjeta.modules.contenido.infrastructure.composition import (
        construir_generador,
        construir_puertos_contenido,
    )

    settings = get_settings()
    gen = construir_generador(settings)
    assert gen.nombre == "simulacion"
    async with sm() as s:
        puertos = construir_puertos_contenido(s, settings)
    assert puertos.config.cuota_mensual >= 1
    assert puertos.almacen.url_publica("x/y.png").endswith("x/y.png")


async def test_moderacion_aprueba_desde_la_cola(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    pieza = await _generar(sm, almacen, comercio=comercio, auto=False)
    assert pieza.estado is EstadoPieza.EN_MODERACION
    async with sm() as s:
        cola = await ModeracionPiezas(_puertos(s, almacen)).cola()
        assert any(p.id == pieza.id for p in cola)
        await ModeracionPiezas(_puertos(s, almacen)).aprobar(id_pieza=str(pieza.id))
    async with sm() as s:
        recargada = await _puertos(s, almacen).piezas.obtener(pieza.id)
    assert recargada is not None and recargada.publicable is True


async def test_retencion_por_promociones_vencidas(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    from tarjeta.modules.contenido.application.retencion import Retencion

    comercio = str(uuid.uuid4())
    id_promocion = str(uuid.uuid4())
    async with sm() as s:
        await GenerarPieza(_puertos(s, almacen)).ejecutar(
            id_comercio=comercio,
            id_promocion=id_promocion,
            idea="empanadas",
            rubro="gastronomía",
            nombre_fantasia="La Nona",
            mecanica="PORCENTAJE",
            estilo_plantilla="clasica",
            superposicion=_superpos(),
            plantilla="clasica",
            auto_aprueba=True,
            periodo=PERIODO,
        )
    async with sm() as s:
        borradas = await Retencion(_puertos(s, almacen)).purgar_de_promociones([id_promocion])
    assert borradas == 1


async def test_foto_propia_no_gasta_credito_ni_marca_agua(sm: async_sessionmaker, almacen) -> None:  # type: ignore[no-untyped-def]
    comercio = str(uuid.uuid4())
    buf = BytesIO()
    Image.new("RGB", (512, 512), (200, 120, 60)).save(buf, format="PNG")
    async with sm() as s:
        pieza = await CrearPiezaDesdeFoto(_puertos(s, almacen)).ejecutar(
            id_comercio=comercio,
            id_promocion=str(uuid.uuid4()),
            foto=buf.getvalue(),
            superposicion=_superpos(),
            plantilla="clasica",
            auto_aprueba=True,
        )
    assert pieza.generada_por_ia is False and len(pieza.formatos) == 3
    assert await _usados(sm, comercio) == 0  # el camino sin IA no consume crédito
