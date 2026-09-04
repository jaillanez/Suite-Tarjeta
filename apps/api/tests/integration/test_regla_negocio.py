"""Integración: regla de negocio §12.1 — comercio validado por cada camino y padrón que no bloquea.

Requiere PostgreSQL real.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.gating import filtrar_promos_habilitadas  # noqa: E402
from tarjeta.modules.comercios.api.deps import (  # noqa: E402
    ActorComercio,
    requiere_comercio_habilitado,
)
from tarjeta.modules.comercios.domain.comercio import (  # noqa: E402
    Comercio,
    EstadoComercio,
    EvidenciaConvenio,
)
from tarjeta.modules.comercios.domain.errors import ComercioNoHabilitado  # noqa: E402
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio  # noqa: E402
from tarjeta.modules.comercios.domain.roles import RolComercio  # noqa: E402
from tarjeta.modules.comercios.domain.sucursal import Sucursal  # noqa: E402
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio  # noqa: E402
from tarjeta.modules.comercios.infrastructure.composition import (  # noqa: E402
    construir_puertos_comercios,
)
from tarjeta.modules.comercios.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyComercioRepository,
    SqlAlchemySucursalRepository,
    SqlAlchemyUsuarioComercioRepository,
)
from tarjeta.modules.padron.application.consultar import consultar_y_actualizar  # noqa: E402
from tarjeta.modules.padron.domain.errors import PadronNoDisponible  # noqa: E402
from tarjeta.modules.padron.domain.estado_padron import EstadoPadron  # noqa: E402
from tarjeta.modules.padron.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyEstadoPadronRepository,
)
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento  # noqa: E402
from tarjeta.modules.promociones.domain.promocion import Promocion  # noqa: E402
from tarjeta.modules.promociones.domain.vigencia import Vigencia  # noqa: E402
from tarjeta.modules.promociones.infrastructure.composition import (  # noqa: E402
    construir_puertos_promociones,
)
from tarjeta.shared.domain.types import EntityId  # noqa: E402
from tarjeta.shared.infrastructure.crypto import FieldCipher  # noqa: E402
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox  # noqa: E402

_settings = get_settings()

_RUTA = {
    EstadoComercio.SOLICITADA: [],
    EstadoComercio.APROBADA: [EstadoComercio.EN_REVISION, EstadoComercio.APROBADA],
    EstadoComercio.ACTIVA: [
        EstadoComercio.EN_REVISION,
        EstadoComercio.APROBADA,
        EstadoComercio.ACTIVA,
    ],
}


@pytest.fixture
async def sm() -> AsyncIterator[async_sessionmaker]:
    eng = create_async_engine(str(_settings.database_url))
    try:
        async with eng.connect() as c:
            await c.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await eng.dispose()
        pytest.skip(f"Base no disponible: {exc}")
    yield async_sessionmaker(eng, expire_on_commit=False)
    await eng.dispose()


async def _comercio(sm: async_sessionmaker, *, estado: EstadoComercio) -> Comercio:
    c = Comercio.solicitar(
        cuit=str(uuid.uuid4().int)[:11],
        razon_social="Comercio Test SA",
        nombre_fantasia="La Nona",
        rubro="gastronomia",
        logo_url="",
        id_responsable=EntityId.new(),
        convenio=EvidenciaConvenio(version="v1", fecha=datetime.now(UTC), ip="1.1.1.1"),
    )
    for destino in _RUTA[estado]:
        c.transicionar(destino)
    async with sm() as s:
        await SqlAlchemyComercioRepository(s).agregar(c)
        await s.commit()
    return c


async def _sucursal(sm: async_sessionmaker, id_comercio: EntityId, lat: float, lon: float) -> None:
    suc = Sucursal.crear(
        id_comercio=id_comercio, nombre="Central", direccion="Calle 1", lat=lat, lon=lon
    )
    async with sm() as s:
        await SqlAlchemySucursalRepository(s).agregar(suc)
        await s.commit()


async def _promo(sm: async_sessionmaker, id_comercio: EntityId) -> Promocion:
    async with sm() as s:
        promo = Promocion.crear(
            id_comercio=id_comercio,
            titulo="Promo",
            descripcion="",
            mecanica=Mecanica.PORCENTAJE,
            segmento=Segmento.AMBOS,
            valor_platino=10,
            valor_black=20,
            vigencia=Vigencia(
                fecha_desde=datetime(2026, 1, 1).date(), fecha_hasta=datetime(2027, 12, 31).date()
            ),
            sucursales=[EntityId.new()],
        )
        promo.activar()
        await construir_puertos_promociones(s).promociones.agregar(promo)
        await s.commit()
    return promo


# --------------------------------------------------------------- BR-2: mapa


async def test_mapa_excluye_comercio_no_aprobado(sm: async_sessionmaker) -> None:
    lat, lon = -31.53, -68.52  # San Juan
    aprobado = await _comercio(sm, estado=EstadoComercio.APROBADA)
    solicitado = await _comercio(sm, estado=EstadoComercio.SOLICITADA)
    await _sucursal(sm, aprobado.id, lat, lon)
    await _sucursal(sm, solicitado.id, lat, lon)
    async with sm() as s:
        cercanas = await SqlAlchemySucursalRepository(s).cercanas(
            lat=lat, lon=lon, radio_m=1000, limite=50
        )
    nombres = {c.id for c in cercanas}
    # La sucursal del comercio no aprobado no aparece; ambas están ACTIVAS y a la misma distancia.
    async with sm() as s:
        suc_aprob = await SqlAlchemySucursalRepository(s).listar_por_comercio(aprobado.id)
        suc_solic = await SqlAlchemySucursalRepository(s).listar_por_comercio(solicitado.id)
    assert str(suc_aprob[0].id) in nombres
    assert str(suc_solic[0].id) not in nombres


# --------------------------------------------------------------- BR-3: búsqueda / feed / motor


async def test_filtro_de_promos_excluye_comercio_no_aprobado(sm: async_sessionmaker) -> None:
    aprobado = await _comercio(sm, estado=EstadoComercio.APROBADA)
    suspendido = await _comercio(sm, estado=EstadoComercio.ACTIVA)
    # se suspende después de publicar
    async with sm() as s:
        c = await SqlAlchemyComercioRepository(s).obtener(suspendido.id)
        assert c is not None
        c.transicionar(EstadoComercio.SUSPENDIDA)
        await SqlAlchemyComercioRepository(s).guardar(c)
        await s.commit()
    p_ok = await _promo(sm, aprobado.id)
    p_susp = await _promo(sm, suspendido.id)
    async with sm() as s:
        filtradas = await filtrar_promos_habilitadas(s, [p_ok, p_susp])
    ids = {str(p.id) for p in filtradas}
    assert str(p_ok.id) in ids
    assert str(p_susp.id) not in ids  # suspendido después de publicar: fuera


# --------------------------------------------------------------- BR-4: operar canje


async def test_requiere_comercio_habilitado(sm: async_sessionmaker) -> None:
    async def _actor(comercio: Comercio) -> ActorComercio:
        usuario = UsuarioComercio.crear(
            id_comercio=comercio.id, id_persona=EntityId.new(), rol=RolComercio.ADMIN_COMERCIO
        )
        async with sm() as s:
            await SqlAlchemyUsuarioComercioRepository(s).agregar(usuario)
            await s.commit()
        return ActorComercio(usuario)

    dep = requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR)

    aprobado = await _comercio(sm, estado=EstadoComercio.APROBADA)
    solicitado = await _comercio(sm, estado=EstadoComercio.SOLICITADA)
    actor_ok = await _actor(aprobado)
    actor_no = await _actor(solicitado)
    async with sm() as s:
        puertos = construir_puertos_comercios(s, _settings)
        assert (await dep(actor=actor_ok, puertos=puertos)) is actor_ok  # aprobado: opera
    async with sm() as s:
        puertos = construir_puertos_comercios(s, _settings)
        with pytest.raises(ComercioNoHabilitado):
            await dep(actor=actor_no, puertos=puertos)  # solicitud: no opera


# --------------------------------------------------------------- padrón que no bloquea (§12.1)


async def test_padron_caido_no_degrada_nivel(sm: async_sessionmaker) -> None:
    class _PadronCaido:
        async def al_dia(self, dni: str) -> bool:
            raise PadronNoDisponible("caído")

    id_persona = EntityId.new()
    cipher = FieldCipher(
        _settings.field_encryption_key.get_secret_value(),
        _settings.field_encryption_key_version,
    )
    # Estado previo: al día (Black).
    async with sm() as s:
        repo = SqlAlchemyEstadoPadronRepository(s, cipher=cipher)
        await repo.guardar(
            EstadoPadron(
                id_persona=id_persona,
                dni="30000000",
                al_dia=True,
                es_comerciante=False,
                fecha_ultima_consulta=datetime.now(UTC),
            ),
            anterior=None,
            origen="test",
        )
        await s.commit()
    # El padrón se cae: no se cambia el estado conocido (nadie baja de nivel).
    async with sm() as s:
        repo = SqlAlchemyEstadoPadronRepository(s, cipher=cipher)
        await consultar_y_actualizar(
            repo=repo,
            cliente=_PadronCaido(),
            outbox=SqlAlchemyOutbox(s),
            id_persona=id_persona,
            dni="30000000",
            origen="test",
        )
        await s.commit()
    async with sm() as s:
        estado = await SqlAlchemyEstadoPadronRepository(s, cipher=cipher).obtener(id_persona)
    assert estado is not None and estado.al_dia is True  # conservó el nivel previo
