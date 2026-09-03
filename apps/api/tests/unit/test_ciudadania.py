"""Tests unitarios del módulo ciudadania."""

from __future__ import annotations

from tarjeta.modules.ciudadania.application import handlers
from tarjeta.modules.ciudadania.domain.historial_nivel import HistorialNivel
from tarjeta.modules.ciudadania.domain.nivel import REGLA_VIGENTE, Nivel, calcular_nivel
from tarjeta.modules.ciudadania.domain.perfil_ciudadano import PerfilCiudadano
from tarjeta.modules.ciudadania.domain.tarjeta import numero_valido
from tarjeta.shared.domain.types import EntityId


def test_motor_de_nivel() -> None:
    assert calcular_nivel(al_dia=True, excepcion_black_vigente=False) is Nivel.BLACK
    assert calcular_nivel(al_dia=False, excepcion_black_vigente=False) is Nivel.PLATINO
    assert calcular_nivel(al_dia=False, excepcion_black_vigente=True) is Nivel.BLACK
    assert calcular_nivel(al_dia=True, excepcion_black_vigente=True) is Nivel.BLACK


def test_crear_perfil_platino_y_tarjeta() -> None:
    perfil = PerfilCiudadano.crear(EntityId.new())
    assert perfil.nivel is Nivel.PLATINO
    assert numero_valido(perfil.numero_tarjeta)
    assert any(e.name == "TarjetaEmitida" for e in perfil.pull_events())


def test_recalcular_cambia_y_guarda_snapshot() -> None:
    perfil = PerfilCiudadano.crear(EntityId.new())
    hist = perfil.recalcular(al_dia=True, excepcion_black_vigente=False, motivo="cálculo")
    assert perfil.nivel is Nivel.BLACK
    assert isinstance(hist, HistorialNivel)
    assert hist.detalle_regla_aplicada == REGLA_VIGENTE
    # sin cambio -> None
    assert perfil.recalcular(al_dia=True, excepcion_black_vigente=False, motivo="x") is None


# --- fakes -------------------------------------------------------------------
class _FakePerfiles:
    def __init__(self) -> None:
        self._p: dict[EntityId, PerfilCiudadano] = {}

    async def obtener(self, id_persona: EntityId) -> PerfilCiudadano | None:
        return self._p.get(id_persona)

    async def agregar(self, perfil: PerfilCiudadano) -> None:
        self._p[perfil.id] = perfil

    async def guardar(self, perfil: PerfilCiudadano) -> None:
        self._p[perfil.id] = perfil


class _FakeHistorial:
    def __init__(self) -> None:
        self.items: list[HistorialNivel] = []

    async def agregar(self, h: HistorialNivel) -> None:
        self.items.append(h)


class _FakeExcepciones:
    def __init__(self, vigente: bool) -> None:
        self._v = vigente

    async def hay_black_vigente(self, id_persona, ahora) -> bool:  # type: ignore[no-untyped-def]
        return self._v


class _FakeOutbox:
    async def escribir(self, eventos) -> None:  # type: ignore[no-untyped-def]
        return None


async def test_crear_perfil_handler() -> None:
    perfiles = _FakePerfiles()
    pid = EntityId.new()
    await handlers.crear_perfil_al_verificar(
        perfiles=perfiles, outbox=_FakeOutbox(), id_persona=pid
    )
    assert await perfiles.obtener(pid) is not None


async def test_excepcion_vencida_deja_de_aplicar() -> None:
    perfiles, historial = _FakePerfiles(), _FakeHistorial()
    pid = EntityId.new()
    perfil = PerfilCiudadano.crear(pid)
    perfil.recalcular(al_dia=True, excepcion_black_vigente=False, motivo="al día")  # BLACK
    await perfiles.agregar(perfil)

    # Excepción vencida (hay_black_vigente=False) y ya no está al día -> vuelve a PLATINO solo.
    await handlers.recalcular_nivel(
        perfiles=perfiles,
        historial=historial,
        excepciones=_FakeExcepciones(vigente=False),
        outbox=_FakeOutbox(),
        id_persona=pid,
        al_dia=False,
        motivo="cálculo automático",
    )
    assert (await perfiles.obtener(pid)).nivel is Nivel.PLATINO  # type: ignore[union-attr]


async def test_excepcion_vigente_mantiene_black() -> None:
    perfiles, historial = _FakePerfiles(), _FakeHistorial()
    pid = EntityId.new()
    await perfiles.agregar(PerfilCiudadano.crear(pid))
    await handlers.recalcular_nivel(
        perfiles=perfiles,
        historial=historial,
        excepciones=_FakeExcepciones(vigente=True),
        outbox=_FakeOutbox(),
        id_persona=pid,
        al_dia=False,
        motivo="excepción",
    )
    assert (await perfiles.obtener(pid)).nivel is Nivel.BLACK  # type: ignore[union-attr]
