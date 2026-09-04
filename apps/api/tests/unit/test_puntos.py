"""Unit: dominio de puntos y orden de la caja con puntos (§09)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tarjeta.modules.canje.application.ordenar import PromoParaCaja, ordenar_por_descuento
from tarjeta.modules.puntos.application.contabilidad import sumar_meses
from tarjeta.modules.puntos.domain.billetera import Billetera
from tarjeta.modules.puntos.domain.catalogo import ItemCatalogo
from tarjeta.modules.puntos.domain.moneda import (
    COMERCIO_MUNICIPAL,
    OrigenPuntos,
    TipoMoneda,
    TipoTitular,
    puntos_comercio_por_canje,
)
from tarjeta.modules.puntos.domain.movimiento import MovimientoBilletera, TipoMovimiento
from tarjeta.shared.domain.types import EntityId

_ORIGEN = OrigenPuntos.INDIVIDUAL
_AHORA = datetime.now(UTC)


def test_puntos_por_canje_solo_multiplicador() -> None:
    # 2x sobre base 1 por 100 pesos => 2% de 1000 = 20.
    assert puntos_comercio_por_canje("MULTIPLICADOR_PUNTOS", 200, 1000) == 20
    # Otras mecánicas no otorgan puntos (dan descuento en pesos).
    assert puntos_comercio_por_canje("PORCENTAJE", 20, 1000) == 0
    assert puntos_comercio_por_canje("MULTIPLICADOR_PUNTOS", 0, 1000) == 0
    assert puntos_comercio_por_canje("MULTIPLICADOR_PUNTOS", 200, 0) == 0


def test_billetera_pm_usa_centinela_municipal() -> None:
    pm = Billetera.crear(
        tipo_titular=TipoTitular.PERSONA,
        id_titular="p1",
        tipo_moneda=TipoMoneda.PM,
        id_comercio=None,
    )
    assert pm.id_comercio == COMERCIO_MUNICIPAL
    assert pm.saldo == 0


def test_billetera_pc_exige_comercio() -> None:
    with pytest.raises(ValueError):
        Billetera.crear(
            tipo_titular=TipoTitular.PERSONA,
            id_titular="p1",
            tipo_moneda=TipoMoneda.PC,
            id_comercio=None,
        )


def test_movimiento_valida_signo_y_tipo() -> None:
    # Acreditar con monto negativo es inconsistente.
    with pytest.raises(ValueError):
        MovimientoBilletera(
            id=EntityId.new(),
            id_billetera=EntityId.new(),
            tipo=TipoMovimiento.ACREDITACION,
            monto=-5,
            origen_puntos=_ORIGEN,
            creado_en=_AHORA,
        )
    # Consumir con monto positivo también.
    with pytest.raises(ValueError):
        MovimientoBilletera(
            id=EntityId.new(),
            id_billetera=EntityId.new(),
            tipo=TipoMovimiento.CONSUMO,
            monto=5,
            origen_puntos=_ORIGEN,
            creado_en=_AHORA,
        )


def test_item_catalogo_disponible() -> None:
    item = ItemCatalogo.crear(
        titulo="Entrada",
        descripcion="",
        costo_pm=100,
        stock=1,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 12, 31),
    )
    assert item.disponible(date(2026, 6, 1)) is True
    assert item.disponible(date(2027, 1, 1)) is False  # fuera de vigencia
    item.stock = 0
    assert item.disponible(date(2026, 6, 1)) is False  # sin stock


def test_sumar_meses_recorta_el_dia() -> None:
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 1, 1), 24) == date(2028, 1, 1)


def test_orden_caja_incorpora_valor_de_los_puntos() -> None:
    # Deuda §09.0.B: MULTIPLICADOR_PUNTOS descuenta 0 pesos pero otorga puntos.
    promos = [
        PromoParaCaja(id="desc", titulo="10%", mecanica="PORCENTAJE", valor=10, puntos=0),
        PromoParaCaja(
            id="mult", titulo="x2 puntos", mecanica="MULTIPLICADOR_PUNTOS", valor=200, puntos=20
        ),
    ]
    # Sin valorar los puntos, el descuento en pesos gana y el multiplicador queda último.
    r0 = ordenar_por_descuento(promos, 1000, valor_punto=0)
    assert r0[0].id == "desc"
    assert r0[-1].id == "mult"
    # Valorando los puntos (20 pts * 10 = 200 > 100), el multiplicador pasa a proponerse primero.
    r = ordenar_por_descuento(promos, 1000, valor_punto=10)
    assert r[0].id == "mult"
    assert r[0].beneficio == 200
