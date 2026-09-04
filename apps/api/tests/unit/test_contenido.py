"""Unit: dominio de contenido (prompt, estados de la pieza, plantillas). §11."""

from __future__ import annotations

import pytest

from tarjeta.modules.contenido.domain.errors import TransicionPiezaInvalida
from tarjeta.modules.contenido.domain.pieza import Pieza, Superposicion
from tarjeta.modules.contenido.domain.plantillas import PLANTILLAS
from tarjeta.modules.contenido.domain.prompt import RESTRICCIONES_FIJAS, componer_prompt
from tarjeta.modules.contenido.domain.tipos import TAMANOS, FormatoPieza, OrigenPieza


def _pieza(origen: OrigenPieza = OrigenPieza.IA) -> Pieza:
    return Pieza.crear(
        id_comercio="c1",
        id_promocion="p1",
        origen=origen,
        plantilla="clasica",
        idea_texto="empanadas caseras",
        prompt_usado="",
        superposicion=Superposicion(
            porcentaje="20%", vigencia="Hasta 2026-12-31", nombre="La Nona"
        ),
        imagen_fondo_clave="k",
        variantes_claves=["k"],
        modelo_ia="simulacion",
    )


def test_prompt_combina_las_cuatro_partes() -> None:
    p = componer_prompt(
        "empanadas caseras",
        rubro="gastronomía",
        nombre_fantasia="La Nona",
        mecanica="PORCENTAJE",
        estilo_plantilla="clasica",
    )
    assert "empanadas caseras" in p  # 1) idea original
    assert "gastronomía" in p and "La Nona" in p and "PORCENTAJE" in p  # 2) datos de la promo
    assert "clasica" in p  # 3) plantilla de marca
    assert RESTRICCIONES_FIJAS in p  # 4) restricciones fijas de seguridad


def test_al_menos_seis_plantillas_por_formato() -> None:
    # Cada plantilla sirve para los tres formatos, así que basta con contar las plantillas.
    assert len(PLANTILLAS) >= 6
    assert set(TAMANOS) == set(FormatoPieza)


def test_pieza_ia_lleva_metadato_de_origen() -> None:
    p = _pieza(OrigenPieza.IA)
    assert p.generada_por_ia is True and p.modelo_ia == "simulacion"
    foto = _pieza(OrigenPieza.FOTO_PROPIA)
    assert foto.generada_por_ia is False


def test_pieza_rechazada_no_es_publicable_ni_se_reaprueba() -> None:
    p = _pieza()
    p.enviar_a_moderacion()
    p.rechazar("producto engañoso")
    assert p.publicable is False
    with pytest.raises(TransicionPiezaInvalida):
        p.aprobar()  # §11.6: una pieza rechazada no vuelve a ser publicable


def test_pieza_aprobada_es_publicable() -> None:
    p = _pieza()
    p.aprobar()  # confianza VERIFICADO: aprueba desde borrador
    assert p.publicable is True
