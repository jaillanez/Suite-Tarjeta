"""Unit: dominio del módulo promociones (mecánicas, vigencia, estados, confianza)."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from tarjeta.modules.promociones.domain.confianza import (
    NivelConfianza,
    PerfilConfianza,
    requiere_revision_previa,
)
from tarjeta.modules.promociones.domain.errors import (
    PromocionActivaInmutable,
    SegmentoNoAplica,
    TopeInvalido,
    TransicionPromocionInvalida,
)
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento, beneficio_relativo
from tarjeta.modules.promociones.domain.promocion import EstadoPromocion, Promocion
from tarjeta.modules.promociones.domain.vigencia import Vigencia
from tarjeta.shared.domain.types import EntityId


def _vig(**kw: object) -> Vigencia:
    base: dict = {"fecha_desde": date(2026, 1, 1), "fecha_hasta": date(2026, 12, 31)}
    base.update(kw)
    return Vigencia(**base)  # type: ignore[arg-type]


def _promo(**kw: object) -> Promocion:
    base: dict = {
        "id_comercio": EntityId.new(),
        "titulo": "Descuento",
        "descripcion": "",
        "mecanica": Mecanica.PORCENTAJE,
        "segmento": Segmento.AMBOS,
        "valor_platino": 10,
        "valor_black": 20,
        "vigencia": _vig(),
        "sucursales": [EntityId.new()],
    }
    base.update(kw)
    return Promocion.crear(**base)  # type: ignore[arg-type]


# ------------------------------------------------------------------ mecánicas / segmento


def test_siete_mecanicas() -> None:
    assert {m.value for m in Mecanica} == {
        "PORCENTAJE",
        "MONTO_FIJO",
        "DOS_POR_UNO",
        "PRECIO_ESPECIAL",
        "MULTIPLICADOR_PUNTOS",
        "CUPON_UNICO",
        "COMBO",
    }


def test_valores_diferenciados_por_nivel() -> None:
    p = _promo(valor_platino=10, valor_black=20)
    assert p.valor_para("PLATINO") == 10
    assert p.valor_para("BLACK") == 20
    assert p.beneficio_para("BLACK") > p.beneficio_para("PLATINO")


def test_exclusiva_black_no_lleva_valor_platino() -> None:
    with pytest.raises(SegmentoNoAplica):
        _promo(segmento=Segmento.SOLO_BLACK, valor_platino=10)


def test_platino_no_aplica_a_exclusiva_black() -> None:
    p = _promo(segmento=Segmento.SOLO_BLACK, valor_platino=None, valor_black=30)
    assert p.aplica_a_nivel("BLACK") is True
    assert p.aplica_a_nivel("PLATINO") is False


def test_beneficio_relativo_2x1_alto() -> None:
    assert beneficio_relativo(Mecanica.DOS_POR_UNO, 0) == 50.0
    assert beneficio_relativo(Mecanica.PORCENTAJE, 30) == 30.0
    # Precio especial: menor precio => mayor beneficio.
    assert beneficio_relativo(Mecanica.PRECIO_ESPECIAL, 100) > beneficio_relativo(
        Mecanica.PRECIO_ESPECIAL, 200
    )


# ------------------------------------------------------------------ vigencia (tz, medianoche)


def test_vigencia_por_fecha() -> None:
    v = _vig(fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 30))
    assert v.vigente_en(datetime(2026, 6, 15, 12, 0)) is True
    assert v.vigente_en(datetime(2026, 5, 31, 12, 0)) is False


def test_vigencia_por_dia_de_semana() -> None:
    v = _vig(dias_semana=frozenset({0, 2}))  # lunes y miércoles
    assert v.vigente_en(datetime(2026, 9, 7, 12, 0)) is True  # lunes
    assert v.vigente_en(datetime(2026, 9, 8, 12, 0)) is False  # martes


def test_vigencia_franja_normal() -> None:
    v = _vig(hora_desde=time(9, 0), hora_hasta=time(18, 0))
    assert v.vigente_en(datetime(2026, 6, 15, 10, 0)) is True
    assert v.vigente_en(datetime(2026, 6, 15, 8, 0)) is False
    assert v.vigente_en(datetime(2026, 6, 15, 18, 0)) is False  # borde: 18:00 excluido


def test_vigencia_franja_cruza_medianoche() -> None:
    v = _vig(hora_desde=time(22, 0), hora_hasta=time(2, 0))
    assert v.vigente_en(datetime(2026, 6, 15, 23, 0)) is True
    assert v.vigente_en(datetime(2026, 6, 15, 1, 0)) is True
    assert v.vigente_en(datetime(2026, 6, 15, 12, 0)) is False


# ------------------------------------------------------------------ máquina de estados


def test_flujo_estados_valido() -> None:
    p = _promo()
    assert p.estado is EstadoPromocion.BORRADOR
    p.enviar_a_revision()
    p.aprobar()
    p.activar()
    assert p.estado is EstadoPromocion.ACTIVA
    p.pausar()
    p.reanudar()
    p.vencer()
    assert p.estado is EstadoPromocion.VENCIDA


def test_transicion_invalida() -> None:
    p = _promo()
    with pytest.raises(TransicionPromocionInvalida):
        p.aprobar()  # BORRADOR -> APROBADA no existe (falta EN_REVISION)


def test_rechazada_es_terminal() -> None:
    p = _promo()
    p.enviar_a_revision()
    p.rechazar("no cumple")
    with pytest.raises(TransicionPromocionInvalida):
        p.activar()


def test_publicacion_directa_borrador_a_activa() -> None:
    p = _promo()
    p.activar()  # comercio de confianza publica directo
    assert p.estado is EstadoPromocion.ACTIVA


# ------------------------------------------------------------------ reglas económicas


def test_activa_no_edita_condiciones_economicas() -> None:
    p = _promo()
    p.activar()
    with pytest.raises(PromocionActivaInmutable):
        p.editar_condiciones_economicas(
            mecanica=Mecanica.PORCENTAJE, valor_platino=5, valor_black=10, tope_total=None
        )


def test_tope_no_baja_de_usos_consumidos() -> None:
    p = _promo(tope_total=100)
    p.usos_totales = 40
    with pytest.raises(TopeInvalido):
        p.editar_condiciones_economicas(
            mecanica=Mecanica.PORCENTAJE, valor_platino=10, valor_black=20, tope_total=30
        )


def test_tope_negativo_rechazado() -> None:
    with pytest.raises(TopeInvalido):
        _promo(tope_total=0)


def test_editar_presentacion_permitido_en_activa() -> None:
    p = _promo()
    p.activar()
    p.editar_presentacion(titulo="Nuevo", descripcion="d", imagen_url="u")
    assert p.titulo == "Nuevo"  # el título no es condición económica


# ------------------------------------------------------------------ confianza


def test_confianza_promueve_por_historial() -> None:
    perfil = PerfilConfianza(id=EntityId.new())
    assert perfil.nivel is NivelConfianza.NUEVO
    assert requiere_revision_previa(perfil.nivel) is True
    for _ in range(3):
        perfil.registrar_aprobacion(umbral_establecido=3, umbral_verificado=10)
    assert perfil.nivel is NivelConfianza.ESTABLECIDO
    assert requiere_revision_previa(perfil.nivel) is False
    for _ in range(7):
        perfil.registrar_aprobacion(umbral_establecido=3, umbral_verificado=10)
    assert perfil.nivel is NivelConfianza.VERIFICADO
