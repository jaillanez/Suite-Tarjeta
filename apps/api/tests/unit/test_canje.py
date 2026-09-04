"""Unit: dominio del módulo canje (descuento real, orden, estados, tokens)."""

from __future__ import annotations

import time as _time
from datetime import UTC, datetime, timedelta

import pytest

from tarjeta.modules.canje.application.operaciones import formato_comprobante
from tarjeta.modules.canje.application.ordenar import PromoParaCaja, ordenar_por_descuento
from tarjeta.modules.canje.domain.descuento import calcular_descuento, requiere_cantidad
from tarjeta.modules.canje.domain.errors import (
    ConfirmacionVencida,
    ConfirmadorInvalido,
    FueraDeVentanaAnulacion,
    TransicionCanjeInvalida,
)
from tarjeta.modules.canje.domain.transaccion import (
    Confirmador,
    EstadoTransaccion,
    Transaccion,
    ViaCanje,
)
from tarjeta.modules.canje.infrastructure.tokens import FirmadorTokenCiudadano
from tarjeta.modules.promociones.domain.mecanica import Mecanica, beneficio_relativo

# ------------------------------------------------------------------ descuento real


def test_descuento_por_mecanica() -> None:
    assert calcular_descuento("PORCENTAJE", 20, 1000) == 200
    assert calcular_descuento("MONTO_FIJO", 300, 1000) == 300
    assert calcular_descuento("MONTO_FIJO", 3000, 1000) == 1000  # no supera el monto
    assert calcular_descuento("PRECIO_ESPECIAL", 500, 1000) == 500
    assert calcular_descuento("DOS_POR_UNO", 0, 1000) == 500
    assert calcular_descuento("MULTIPLICADOR_PUNTOS", 200, 1000) == 0  # es puntos, no pesos


def test_mecanicas_por_cantidad_no_se_proponen() -> None:
    assert requiere_cantidad("DOS_POR_UNO") is True
    assert requiere_cantidad("COMBO") is True
    assert requiere_cantidad("PORCENTAJE") is False


def test_orden_por_descuento_real_vs_heuristica() -> None:
    # Caso construido: la heurística ordena distinto al descuento real en pesos.
    monto = 1000
    promos = [
        PromoParaCaja(id="a", titulo="Porcentaje 10", mecanica="PORCENTAJE", valor=10),
        PromoParaCaja(id="b", titulo="Precio especial", mecanica="PRECIO_ESPECIAL", valor=500),
    ]
    real = [o.id for o in ordenar_por_descuento(promos, monto)]
    # Heurística de promociones (sin monto): ordena por beneficio_relativo.
    heur = sorted(
        promos,
        key=lambda p: beneficio_relativo(Mecanica(p.mecanica), p.valor),
        reverse=True,
    )
    heuristico = [p.id for p in heur]
    assert real == ["b", "a"]  # real: precio especial ahorra 500 > 100
    assert heuristico == ["a", "b"]  # heurística: 10% > 1/500
    assert real != heuristico


def test_dos_por_uno_no_es_auto_propuesta() -> None:
    promos = [
        PromoParaCaja(id="x", titulo="2x1", mecanica="DOS_POR_UNO", valor=0),
        PromoParaCaja(id="y", titulo="15%", mecanica="PORCENTAJE", valor=15),
    ]
    opciones = {o.id: o for o in ordenar_por_descuento(promos, 1000)}
    assert opciones["x"].auto_propuesta is False  # 2x1 aparece pero no se propone sola
    assert opciones["y"].auto_propuesta is True
    # La primera (auto-propuesta) es la de porcentaje, no el 2x1.
    assert ordenar_por_descuento(promos, 1000)[0].id == "y"


def test_comprobante_formato() -> None:
    assert formato_comprobante("RIV", 123456) == "RIV-000123456"


# ------------------------------------------------------------------ máquina de estados


def _tx(via: ViaCanje = ViaCanje.CAJERO_ESCANEA, ttl: int = 90) -> Transaccion:
    return Transaccion.crear(
        numero_comprobante="RIV-000000001",
        id_persona="p1",
        nivel_aplicado="BLACK",
        id_comercio="c1",
        id_sucursal="s1",
        id_cajero="k1",
        id_promocion="pr1",
        monto_bruto=1000,
        descuento=200,
        via=via,
        clave_idempotencia="clave-1",
        ttl_confirmacion_seg=ttl,
    )


def test_total_pagar() -> None:
    t = _tx()
    assert t.total_pagar == 800
    assert t.puntos_ciudadano == 0 and t.puntos_municipio == 0  # §08.1


def test_confirmador_por_via() -> None:
    assert _tx(ViaCanje.CAJERO_ESCANEA).confirmador is Confirmador.CIUDADANO
    assert _tx(ViaCanje.CODIGO).confirmador is Confirmador.CIUDADANO
    assert _tx(ViaCanje.CIUDADANO_ESCANEA).confirmador is Confirmador.CAJERO
    assert _tx(ViaCanje.TARJETA_FISICA).confirmador is Confirmador.CAJERO


def test_confirmar_por_parte_incorrecta_falla() -> None:
    t = _tx(ViaCanje.CAJERO_ESCANEA)  # confirma el ciudadano
    with pytest.raises(ConfirmadorInvalido):
        t.confirmar(por=Confirmador.CAJERO)
    t.confirmar(por=Confirmador.CIUDADANO)
    assert t.estado is EstadoTransaccion.APLICADA


def test_confirmacion_vencida_no_aplica() -> None:
    t = _tx(ttl=90)
    t.vence_en = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ConfirmacionVencida):
        t.confirmar(por=Confirmador.CIUDADANO)


def test_expirar_libera() -> None:
    t = _tx()
    t.expirar()
    assert t.estado is EstadoTransaccion.EXPIRADA


def test_anulacion_dentro_de_ventana() -> None:
    t = _tx()
    t.confirmar(por=Confirmador.CIUDADANO)
    t.anular(motivo="error de carga", ventana_minutos=15, es_admin=False)
    assert t.estado is EstadoTransaccion.ANULADA


def test_anulacion_fuera_de_ventana_solo_admin() -> None:
    t = _tx()
    t.confirmar(por=Confirmador.CIUDADANO)
    t.confirmada_en = datetime.now(UTC) - timedelta(minutes=30)
    with pytest.raises(FueraDeVentanaAnulacion):
        t.anular(motivo="tarde", ventana_minutos=15, es_admin=False)
    t.anular(motivo="tarde, pero admin", ventana_minutos=15, es_admin=True)
    assert t.estado is EstadoTransaccion.ANULADA


def test_no_se_anula_lo_no_aplicado() -> None:
    t = _tx()
    with pytest.raises(TransicionCanjeInvalida):
        t.anular(motivo="x", ventana_minutos=15, es_admin=True)


# ------------------------------------------------------------------ tokens del ciudadano


def test_token_verifica_y_congela_nivel() -> None:
    f = FirmadorTokenCiudadano("secreto")
    ahora = int(_time.time())
    lote = f.emitir_lote(id_persona="p1", nivel="BLACK", ahora_epoch=ahora, horas=1)
    actual = lote[0]
    datos = f.verificar(actual.token, ahora_epoch=ahora)
    assert datos is not None
    assert datos.id_persona == "p1"
    assert datos.nivel == "BLACK"  # nivel congelado en el token


def test_token_futuro_todavia_no_vale_y_pasado_vence() -> None:
    f = FirmadorTokenCiudadano("secreto")
    ahora = int(_time.time())
    lote = f.emitir_lote(id_persona="p1", nivel="PLATINO", ahora_epoch=ahora, horas=1)
    # Un token de una ventana futura no es válido ahora.
    futuro = lote[10]
    assert f.verificar(futuro.token, ahora_epoch=ahora) is None
    # El token actual, 200 s después, ya venció (validez 90 s).
    assert f.verificar(lote[0].token, ahora_epoch=ahora + 200) is None


def test_token_tamper_rechazado() -> None:
    f = FirmadorTokenCiudadano("secreto")
    ahora = int(_time.time())
    token = f.emitir_lote(id_persona="p1", nivel="BLACK", ahora_epoch=ahora)[0].token
    cuerpo, _, _firma = token.partition(".")
    assert f.verificar(f"{cuerpo}.firmafalsa", ahora_epoch=ahora) is None
    assert f.verificar("sinpunto", ahora_epoch=ahora) is None
