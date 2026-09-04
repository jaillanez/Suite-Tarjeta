"""Integración: grupo familiar — quién crea, herencia por evento, pozo común, sucesión,
antifraude observe-only. Requiere PostgreSQL real.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.herencia import es_black_propio_al_dia, recalcular_persona  # noqa: E402
from tarjeta.modules.ciudadania.domain.nivel import Nivel, NivelOrigen  # noqa: E402
from tarjeta.modules.ciudadania.domain.perfil_ciudadano import PerfilCiudadano  # noqa: E402
from tarjeta.modules.ciudadania.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.grupo.application.casos import (  # noqa: E402
    AceptarInvitacion,
    CrearGrupo,
    InvitarMiembro,
    SalirDelGrupo,
)
from tarjeta.modules.grupo.domain.errors import NoPuedeCrearGrupo, YaPerteneceAGrupo  # noqa: E402
from tarjeta.modules.grupo.domain.tipos import ModoBilletera  # noqa: E402
from tarjeta.modules.grupo.infrastructure.composition import construir_puertos_grupo  # noqa: E402
from tarjeta.modules.grupo.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyGrupoRepository,
)
from tarjeta.modules.padron.domain.estado_padron import EstadoPadron  # noqa: E402
from tarjeta.modules.padron.domain.events import EstadoPadronActualizado  # noqa: E402
from tarjeta.modules.padron.infrastructure.repositories import (  # noqa: E402
    SqlAlchemyEstadoPadronRepository,
)
from tarjeta.modules.puntos.application.contabilidad import Contabilidad  # noqa: E402
from tarjeta.modules.puntos.application.pozo import TraspasarPozo  # noqa: E402
from tarjeta.modules.puntos.domain.errors import SaldoInsuficiente  # noqa: E402
from tarjeta.modules.puntos.domain.moneda import OrigenPuntos, TipoMoneda, TipoTitular  # noqa: E402
from tarjeta.modules.puntos.infrastructure.composition import (  # noqa: E402
    construir_puertos_puntos,
)
from tarjeta.orquestacion import build_dispatcher  # noqa: E402
from tarjeta.shared.infrastructure.crypto import FieldCipher  # noqa: E402
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox  # noqa: E402

_settings = get_settings()
_dispatcher = build_dispatcher(_settings)


def _cipher() -> FieldCipher:
    return FieldCipher(
        _settings.field_encryption_key.get_secret_value(),
        _settings.field_encryption_key_version,
    )


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


async def _drain(sm: async_sessionmaker) -> None:
    for _ in range(20):
        async with sm() as s:
            n = await _dispatcher.drain(s)
        if n == 0:
            break


async def _ciudadano(sm: async_sessionmaker, *, al_dia: bool) -> str:
    from tarjeta.shared.domain.types import EntityId

    pid = str(uuid.uuid4())
    async with sm() as s:
        await SqlAlchemyPerfilCiudadanoRepository(s).agregar(
            PerfilCiudadano.crear(EntityId.from_str(pid))
        )
        await SqlAlchemyEstadoPadronRepository(s, cipher=_cipher()).guardar(
            EstadoPadron(
                id_persona=EntityId.from_str(pid),
                dni=str(uuid.uuid4().int)[:8],
                al_dia=al_dia,
                es_comerciante=False,
                fecha_ultima_consulta=datetime.now(UTC),
            ),
            anterior=None,
            origen="test",
        )
        await s.commit()
    async with sm() as s:
        await recalcular_persona(s, _settings, pid, motivo="setup", al_dia=al_dia)
        await s.commit()
    return pid


async def _set_al_dia(sm: async_sessionmaker, pid: str, al_dia: bool) -> None:
    from tarjeta.shared.domain.types import EntityId

    async with sm() as s:
        repo = SqlAlchemyEstadoPadronRepository(s, cipher=_cipher())
        anterior = await repo.obtener(EntityId.from_str(pid))
        await repo.guardar(
            EstadoPadron(
                id_persona=EntityId.from_str(pid),
                dni=anterior.dni if anterior else "30000000",
                al_dia=al_dia,
                es_comerciante=False,
                fecha_ultima_consulta=datetime.now(UTC),
            ),
            anterior=anterior,
            origen="test",
        )
        await SqlAlchemyOutbox(s).escribir([EstadoPadronActualizado(id_persona=pid, al_dia=al_dia)])
        await s.commit()
    await _drain(sm)


async def _nivel(sm: async_sessionmaker, pid: str) -> tuple[Nivel, NivelOrigen]:
    from tarjeta.shared.domain.types import EntityId

    async with sm() as s:
        p = await SqlAlchemyPerfilCiudadanoRepository(s).obtener(EntityId.from_str(pid))
    assert p is not None
    return (p.nivel, p.nivel_origen)


async def _crear_grupo(
    sm: async_sessionmaker, titular: str, modo: ModoBilletera = ModoBilletera.COMUN
) -> str:
    async with sm() as s:
        puede = await es_black_propio_al_dia(s, _settings, titular)
        g = await CrearGrupo(construir_puertos_grupo(s)).ejecutar(
            id_titular=titular, modo=modo, es_black_propio_al_dia=puede
        )
    return str(g.id)


async def _sumar(sm: async_sessionmaker, id_grupo: str, titular: str, invitado: str) -> None:
    async with sm() as s:
        inv = await InvitarMiembro(construir_puertos_grupo(s)).ejecutar(
            id_grupo=id_grupo, id_actor=titular, ip="1.2.3.4"
        )
    async with sm() as s:
        await AceptarInvitacion(construir_puertos_grupo(s)).ejecutar(
            token=inv.token, id_invitado=invitado
        )
    await _drain(sm)


# --------------------------------------------------------------- quién puede crear


async def test_platino_no_puede_crear_grupo(sm: async_sessionmaker) -> None:
    platino = await _ciudadano(sm, al_dia=False)
    async with sm() as s:
        puede = await es_black_propio_al_dia(s, _settings, platino)
        with pytest.raises(NoPuedeCrearGrupo):
            await CrearGrupo(construir_puertos_grupo(s)).ejecutar(
                id_titular=platino, modo=ModoBilletera.COMUN, es_black_propio_al_dia=puede
            )


async def test_black_heredado_no_puede_crear_grupo(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    assert await _nivel(sm, miembro) == (Nivel.BLACK, NivelOrigen.HEREDADO_GRUPO)
    # Ese miembro (Black heredado) no puede crear su propio grupo.
    async with sm() as s:
        puede = await es_black_propio_al_dia(s, _settings, miembro)
    assert puede is False


# --------------------------------------------------------------- reglas de composición


async def test_muchos_miembros_sin_tope(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular)
    for _ in range(8):
        await _sumar(sm, gid, titular, await _ciudadano(sm, al_dia=False))
    async with sm() as s:
        from tarjeta.shared.domain.types import EntityId

        miembros = await SqlAlchemyGrupoRepository(s).miembros_activos(EntityId.from_str(gid))
    assert len(miembros) == 9  # titular + 8


async def test_una_persona_un_grupo(sm: async_sessionmaker) -> None:
    t1 = await _ciudadano(sm, al_dia=True)
    t2 = await _ciudadano(sm, al_dia=True)
    persona = await _ciudadano(sm, al_dia=False)
    g1 = await _crear_grupo(sm, t1)
    g2 = await _crear_grupo(sm, t2)
    await _sumar(sm, g1, t1, persona)
    async with sm() as s:
        inv = await InvitarMiembro(construir_puertos_grupo(s)).ejecutar(
            id_grupo=g2, id_actor=t2, ip="1.2.3.4"
        )
    async with sm() as s:
        with pytest.raises(YaPerteneceAGrupo):
            await AceptarInvitacion(construir_puertos_grupo(s)).ejecutar(
                token=inv.token, id_invitado=persona
            )


async def test_salir_e_ingresar_a_otro_es_inmediato(sm: async_sessionmaker) -> None:
    t1 = await _ciudadano(sm, al_dia=True)
    t2 = await _ciudadano(sm, al_dia=True)
    persona = await _ciudadano(sm, al_dia=False)
    g1 = await _crear_grupo(sm, t1)
    g2 = await _crear_grupo(sm, t2)
    await _sumar(sm, g1, t1, persona)
    async with sm() as s:
        await SalirDelGrupo(construir_puertos_grupo(s)).ejecutar(id_grupo=g1, id_persona=persona)
    await _drain(sm)
    # Sin cooldown: se une a otro grupo de inmediato.
    await _sumar(sm, g2, t2, persona)
    assert await _nivel(sm, persona) == (Nivel.BLACK, NivelOrigen.HEREDADO_GRUPO)


# --------------------------------------------------------------- herencia por evento (§10.4)


async def test_titular_cae_y_los_heredados_caen(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    assert (await _nivel(sm, miembro))[0] is Nivel.BLACK
    await _set_al_dia(sm, titular, False)  # el titular se atrasa
    assert (await _nivel(sm, titular))[0] is Nivel.PLATINO
    assert await _nivel(sm, miembro) == (Nivel.PLATINO, NivelOrigen.PROPIO)


async def test_miembro_black_propio_no_cae(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    propio = await _ciudadano(sm, al_dia=True)  # Black por mérito propio
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, propio)
    assert await _nivel(sm, propio) == (Nivel.BLACK, NivelOrigen.PROPIO)
    await _set_al_dia(sm, titular, False)
    assert await _nivel(sm, propio) == (Nivel.BLACK, NivelOrigen.PROPIO)  # no se lo pisa


async def test_titular_recupera_y_los_miembros_tambien(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    await _set_al_dia(sm, titular, False)
    assert (await _nivel(sm, miembro))[0] is Nivel.PLATINO
    await _set_al_dia(sm, titular, True)  # vuelve a estar al día
    assert await _nivel(sm, miembro) == (Nivel.BLACK, NivelOrigen.HEREDADO_GRUPO)


async def test_titular_sale_sin_sucesor_disuelve(sm: async_sessionmaker) -> None:
    from tarjeta.portal_grupo import salir

    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)  # no es Black propio
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    async with sm() as s:
        await salir(SimpleNamespace(id_persona=titular), s)
    await _drain(sm)
    async with sm() as s:
        from tarjeta.shared.domain.types import EntityId

        grupo = await SqlAlchemyGrupoRepository(s).obtener(EntityId.from_str(gid))
    assert grupo is not None and not grupo.activo  # se disolvió
    assert (await _nivel(sm, miembro))[0] is Nivel.PLATINO  # el heredado volvió a su mérito


async def test_titular_sale_con_sucesor_black_propio(sm: async_sessionmaker) -> None:
    from tarjeta.portal_grupo import salir

    titular = await _ciudadano(sm, al_dia=True)
    sucesor = await _ciudadano(sm, al_dia=True)  # Black propio -> puede suceder
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, sucesor)
    async with sm() as s:
        await salir(SimpleNamespace(id_persona=titular), s)
    await _drain(sm)
    async with sm() as s:
        from tarjeta.shared.domain.types import EntityId

        grupo = await SqlAlchemyGrupoRepository(s).obtener(EntityId.from_str(gid))
    assert grupo is not None and grupo.activo and grupo.id_titular == sucesor


# --------------------------------------------------------------- billetera común (§10.5)


async def test_modo_comun_a_individual_traspasa_pozo_al_titular(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular, ModoBilletera.COMUN)
    comercio = str(uuid.uuid4())
    # Pozo del grupo con 100 PC del comercio.
    async with sm() as s:
        await Contabilidad(construir_puertos_puntos(s)).acreditar(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=gid,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=100,
            origen=OrigenPuntos.GRUPO_COMUN,
            concepto="pozo",
        )
        await s.commit()
    async with sm() as s:
        await TraspasarPozo(construir_puertos_puntos(s)).al_titular(
            id_grupo=gid, id_titular=titular
        )
        await s.commit()
    async with sm() as s:
        p = construir_puertos_puntos(s)
        pozo = await p.billeteras.obtener(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=gid,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
        titular_bill = await p.billeteras.obtener(
            tipo_titular=TipoTitular.PERSONA,
            id_titular=titular,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
    assert pozo is not None and pozo.saldo == 0
    assert titular_bill is not None and titular_bill.saldo == 100


async def test_concurrencia_pozo_comun(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular, ModoBilletera.COMUN)
    comercio = str(uuid.uuid4())
    async with sm() as s:
        await Contabilidad(construir_puertos_puntos(s)).acreditar(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=gid,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=100,
            origen=OrigenPuntos.GRUPO_COMUN,
            concepto="pozo",
        )
        await s.commit()

    async def gastar_30() -> bool:
        async with sm() as s:
            try:
                await Contabilidad(construir_puertos_puntos(s)).consumir(
                    tipo_titular=TipoTitular.GRUPO,
                    id_titular=gid,
                    tipo_moneda=TipoMoneda.PC,
                    id_comercio=comercio,
                    puntos=30,
                    concepto="dos miembros a la vez",
                )
                await s.commit()
                return True
            except SaldoInsuficiente:
                return False

    exitos = sum(await asyncio.gather(*(gastar_30() for _ in range(10))))
    assert exitos == 3  # 90 <= 100; el pozo nunca queda en un valor imposible
    async with sm() as s:
        pozo = await construir_puertos_puntos(s).billeteras.obtener(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=gid,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
    assert pozo is not None and pozo.saldo == 10


# --------------------------------------------------------------- panel y antifraude


async def test_panel_no_expone_detalle_de_compras(sm: async_sessionmaker) -> None:
    from tarjeta.portal_grupo import mi_grupo

    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    async with sm() as s:
        panel = await mi_grupo(SimpleNamespace(id_persona=titular), s)
    assert panel.es_titular and panel.id_grupo == gid
    assert len(panel.miembros) == 2  # titular + miembro
    cuerpo = panel.model_dump_json().lower()
    for prohibido in ("compra", "producto", "detalle", "item"):
        assert prohibido not in cuerpo


async def test_gestion_miembro_suspender_tope_reactivar(sm: async_sessionmaker) -> None:
    from tarjeta.modules.grupo.application.casos import GestionMiembro
    from tarjeta.modules.grupo.domain.tipos import EstadoMiembro
    from tarjeta.shared.domain.types import EntityId

    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    async with sm() as s:
        gestion = GestionMiembro(construir_puertos_grupo(s))
        await gestion.fijar_tope(
            id_grupo=gid, id_actor=titular, id_persona=miembro, tope_mensual=500
        )
        await gestion.suspender(id_grupo=gid, id_actor=titular, id_persona=miembro)
    async with sm() as s:
        m = await SqlAlchemyGrupoRepository(s).miembro_en(EntityId.from_str(gid), miembro)
    assert m is not None and m.estado is EstadoMiembro.SUSPENDIDO and m.tope_mensual == 500
    # Suspendido sigue ocupando su grupo (no puede unirse a otro) y sigue heredando el nivel.
    assert (await _nivel(sm, miembro))[0] is Nivel.BLACK
    async with sm() as s:
        await GestionMiembro(construir_puertos_grupo(s)).reactivar(
            id_grupo=gid, id_actor=titular, id_persona=miembro
        )
    async with sm() as s:
        m = await SqlAlchemyGrupoRepository(s).miembro_en(EntityId.from_str(gid), miembro)
    assert m is not None and m.estado is EstadoMiembro.ACTIVO


# --------------------------------------------------------------- deudas del PASO 10


async def test_traspaso_pozo_conserva_el_vencimiento(sm: async_sessionmaker) -> None:
    # §11.0.A: cambiar de modo no debe correr el vencimiento del lote traspasado.

    titular = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular, ModoBilletera.COMUN)
    comercio = str(uuid.uuid4())
    vence = datetime.now(UTC).date() + timedelta(days=100)
    async with sm() as s:
        await Contabilidad(construir_puertos_puntos(s)).acreditar(
            tipo_titular=TipoTitular.GRUPO,
            id_titular=gid,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
            puntos=50,
            origen=OrigenPuntos.GRUPO_COMUN,
            concepto="pozo",
            vence_en=vence,
        )
        await s.commit()
    async with sm() as s:
        await TraspasarPozo(construir_puertos_puntos(s)).al_titular(
            id_grupo=gid, id_titular=titular
        )
        await s.commit()
    async with sm() as s:
        p = construir_puertos_puntos(s)
        bill = await p.billeteras.obtener(
            tipo_titular=TipoTitular.PERSONA,
            id_titular=titular,
            tipo_moneda=TipoMoneda.PC,
            id_comercio=comercio,
        )
        lotes = await p.lotes.disponibles_fifo(bill.id, datetime.now(UTC).date())  # type: ignore[union-attr]
    assert len(lotes) == 1 and lotes[0].vence_en == vence  # conservó el vencimiento original


async def test_miembro_suspendido_puede_salir(sm: async_sessionmaker) -> None:
    # §11.0.B: la suspensión limita el pozo, nunca encierra a nadie en el grupo.
    from tarjeta.modules.grupo.application.casos import GestionMiembro, SalirDelGrupo

    titular = await _ciudadano(sm, al_dia=True)
    miembro = await _ciudadano(sm, al_dia=False)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, miembro)
    async with sm() as s:
        await GestionMiembro(construir_puertos_grupo(s)).suspender(
            id_grupo=gid, id_actor=titular, id_persona=miembro
        )
    async with sm() as s:
        await SalirDelGrupo(construir_puertos_grupo(s)).ejecutar(id_grupo=gid, id_persona=miembro)
    await _drain(sm)
    async with sm() as s:
        assert await SqlAlchemyGrupoRepository(s).miembro_de(miembro) is None  # salió


async def test_sucesor_ve_aviso(sm: async_sessionmaker) -> None:
    # §11.0.C: el sucesor se entera de que ahora es el titular.
    from tarjeta.portal_grupo import salir

    titular = await _ciudadano(sm, al_dia=True)
    sucesor = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular)
    await _sumar(sm, gid, titular, sucesor)
    async with sm() as s:
        await salir(SimpleNamespace(id_persona=titular), s)
    await _drain(sm)
    async with sm() as s:
        avisos = await construir_puertos_grupo(s).avisos.pendientes(sucesor)
    assert any(tipo == "sucesion_titular" for tipo, _txt in avisos)


async def test_antifraude_genera_caso_y_no_bloquea(sm: async_sessionmaker) -> None:
    titular = await _ciudadano(sm, al_dia=True)
    gid = await _crear_grupo(sm, titular)
    # Formación acelerada: varios miembros en pocas horas -> caso, sin frenar ningún alta.
    for _ in range(6):
        await _sumar(sm, gid, titular, await _ciudadano(sm, al_dia=False))
    async with sm() as s:
        alertas = await construir_puertos_grupo(s).alertas.de_grupo(gid)
        from tarjeta.shared.domain.types import EntityId

        miembros = await SqlAlchemyGrupoRepository(s).miembros_activos(EntityId.from_str(gid))
    assert any(a[0] == "formacion_acelerada" for a in alertas)  # generó caso
    assert len(miembros) == 7  # titular + 6: ningún alta se bloqueó
