"""Tests unitarios del módulo padron."""

from __future__ import annotations

import httpx
import pytest

from tarjeta.modules.padron.application import consultar
from tarjeta.modules.padron.domain.errors import PadronNoDisponible, RespuestaPadronInvalida
from tarjeta.modules.padron.domain.estado_padron import EstadoPadron
from tarjeta.modules.padron.infrastructure.cliente_real import ClientePadronReal
from tarjeta.modules.padron.infrastructure.cliente_simulacion import ClientePadronSimulado
from tarjeta.modules.padron.infrastructure.models import (
    EstadoPadronModel,
    HistorialEstadoPadronModel,
)
from tarjeta.shared.domain.types import EntityId

_PROHIBIDAS = (
    "monto",
    "importe",
    "cuenta",
    "cuota",
    "vencimiento",
    "deuda",
    "saldo",
    "fecha_corte",
)


def test_modelo_padron_no_tiene_columnas_de_dinero() -> None:
    for modelo in (EstadoPadronModel, HistorialEstadoPadronModel):
        cols = {c.name for c in modelo.__table__.columns}
        assert not any(any(p in c for p in _PROHIBIDAS) for c in cols), cols


async def test_simulador_regla_par_impar() -> None:
    sim = ClientePadronSimulado()
    assert await sim.al_dia("20000000") is True  # par
    assert await sim.al_dia("20000001") is False  # impar


async def test_simulador_overrides_y_caida() -> None:
    sim = ClientePadronSimulado(al_dia_por_dni={"111": True}, caidos={"999"})
    assert await sim.al_dia("111") is True
    with pytest.raises(PadronNoDisponible):
        await sim.al_dia("999")


# --- fakes para consultar_y_actualizar --------------------------------------
class _FakeRepo:
    def __init__(self, anterior: EstadoPadron | None = None) -> None:
        self._anterior = anterior
        self.guardado: EstadoPadron | None = None

    async def obtener(self, id_persona: EntityId) -> EstadoPadron | None:
        return self._anterior

    async def guardar(self, estado, *, anterior, origen) -> None:  # type: ignore[no-untyped-def]
        self.guardado = estado


class _FakeCliente:
    def __init__(self, *, al_dia: bool = True, caido: bool = False) -> None:
        self._al_dia = al_dia
        self._caido = caido

    async def al_dia(self, dni: str) -> bool:
        if self._caido:
            raise PadronNoDisponible("caído")
        return self._al_dia

    async def es_comerciante(self, cuit: str) -> bool:
        return False


class _FakeOutbox:
    def __init__(self) -> None:
        self.eventos: list[object] = []

    async def escribir(self, eventos: list[object]) -> None:
        self.eventos.extend(eventos)


async def test_consultar_guarda_y_emite() -> None:
    repo, cliente, outbox = _FakeRepo(), _FakeCliente(al_dia=True), _FakeOutbox()
    await consultar.consultar_y_actualizar(
        repo=repo,
        cliente=cliente,
        outbox=outbox,
        id_persona=EntityId.new(),
        dni="20000000",
        origen=consultar.REGISTRO,
    )
    assert repo.guardado is not None and repo.guardado.al_dia is True
    assert len(outbox.eventos) == 1


async def test_degradacion_endpoint_caido_no_cambia_ni_emite() -> None:
    anterior = EstadoPadron(
        id_persona=EntityId.new(),
        dni="20000000",
        al_dia=True,
        es_comerciante=False,
        fecha_ultima_consulta=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    repo, cliente, outbox = _FakeRepo(anterior), _FakeCliente(caido=True), _FakeOutbox()
    await consultar.consultar_y_actualizar(
        repo=repo,
        cliente=cliente,
        outbox=outbox,
        id_persona=EntityId.new(),
        dni="20000000",
        origen=consultar.BATCH,
    )
    assert repo.guardado is None  # no se cambió nada
    assert outbox.eventos == []  # nadie baja de nivel


# --- test de contrato del adaptador real ------------------------------------
async def test_contrato_adaptador_real() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("dni") == "123"
        return httpx.Response(200, json={"al_dia": True})

    cliente = ClientePadronReal(
        base_url="http://x", api_key="k", timeout=2.0, transport=httpx.MockTransport(handler)
    )
    assert await cliente.al_dia("123") is True


async def test_contrato_respuesta_invalida() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"al_dia": "si"})  # no booleano

    cliente = ClientePadronReal(
        base_url="http://x", api_key="k", timeout=2.0, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RespuestaPadronInvalida):
        await cliente.al_dia("123")


async def test_contrato_endpoint_caido() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    cliente = ClientePadronReal(
        base_url="http://x", api_key="k", timeout=2.0, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(PadronNoDisponible):
        await cliente.al_dia("123")
