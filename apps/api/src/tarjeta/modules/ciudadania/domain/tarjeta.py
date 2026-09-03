"""Tarjeta del ciudadano: número de 16 dígitos con dígito verificador (Luhn) y estado."""

from __future__ import annotations

import secrets
from enum import StrEnum


class EstadoTarjeta(StrEnum):
    ACTIVA = "ACTIVA"
    BLOQUEADA = "BLOQUEADA"
    SUSPENDIDA = "SUSPENDIDA"
    BAJA = "BAJA"


def _luhn_check_digit(numero_sin_dv: str) -> int:
    total = 0
    # El dígito verificador ocupa la última posición; los pesos se alternan desde la derecha.
    for i, ch in enumerate(reversed(numero_sin_dv)):
        d = int(ch)
        if i % 2 == 0:  # posición que será par contando el DV a la derecha
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def generar_numero_tarjeta() -> str:
    base = "".join(secrets.choice("0123456789") for _ in range(15))
    return base + str(_luhn_check_digit(base))


def numero_valido(numero: str) -> bool:
    if len(numero) != 16 or not numero.isdigit():
        return False
    return _luhn_check_digit(numero[:15]) == int(numero[15])
