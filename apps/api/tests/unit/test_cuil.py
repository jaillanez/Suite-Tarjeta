"""Validación del dígito verificador del CUIL/CUIT (algoritmo módulo 11)."""

from __future__ import annotations

import pytest

from tarjeta.shared.domain.errors import ValidationError
from tarjeta.shared.domain.types import Cuil, Dni, cuil_check_digit

# CUILs/CUIT con dígito verificador correcto (calculado por módulo 11).
VALIDOS = [
    "20123456786",
    "27123456780",
    "30712345671",
]

# Formato con guiones también debe aceptarse y normalizarse.
VALIDOS_CON_GUIONES = [
    ("20-12345678-6", "20123456786"),
    ("30-71234567-1", "30712345671"),
]

# Dígito verificador incorrecto.
INVALIDOS_DV = [
    "20123456780",
    "27123456781",
    "30712345670",
]


@pytest.mark.parametrize("valor", VALIDOS)
def test_cuil_valido(valor: str) -> None:
    cuil = Cuil(valor)
    assert cuil.value == valor


@pytest.mark.parametrize(("entrada", "esperado"), VALIDOS_CON_GUIONES)
def test_cuil_normaliza_guiones(entrada: str, esperado: str) -> None:
    assert Cuil(entrada).value == esperado


@pytest.mark.parametrize("valor", INVALIDOS_DV)
def test_cuil_digito_verificador_invalido(valor: str) -> None:
    with pytest.raises(ValidationError):
        Cuil(valor)


@pytest.mark.parametrize("valor", ["", "123", "2012345678", "201234567890", "20abc456786"])
def test_cuil_longitud_o_formato_invalido(valor: str) -> None:
    with pytest.raises(ValidationError):
        Cuil(valor)


def test_cuil_expone_dni() -> None:
    assert Cuil("20123456786").dni == Dni("12345678")


def test_cuil_formatea() -> None:
    assert Cuil("20123456786").formatted() == "20-12345678-6"


def test_check_digit_puede_ser_diez_para_invalidos() -> None:
    # Un resultado 10 significa "ningún CUIL válido termina así".
    assert 0 <= cuil_check_digit("2012345678") <= 10


@pytest.mark.parametrize("valor", ["1234567", "12345678"])
def test_dni_valido(valor: str) -> None:
    assert Dni(valor).value == valor


@pytest.mark.parametrize("valor", ["123456", "123456789", "1234x67", ""])
def test_dni_invalido(valor: str) -> None:
    with pytest.raises(ValidationError):
        Dni(valor)
