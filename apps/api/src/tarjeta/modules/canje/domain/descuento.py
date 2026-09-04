"""Cálculo del descuento real en pesos (§08.0.B).

La heurística de `promociones` sirve para ordenar un listado, pero en la caja el orden se
recalcula con el descuento real según el monto. Las mecánicas que dependen de la cantidad de
unidades (2x1, combo) NO se proponen automáticamente: el cajero las elige a mano.

`canje` no importa `promociones` (independencia de módulos): la mecánica llega como string, con
los mismos valores que `promociones.Mecanica`.
"""

from __future__ import annotations

PORCENTAJE = "PORCENTAJE"
MONTO_FIJO = "MONTO_FIJO"
DOS_POR_UNO = "DOS_POR_UNO"
PRECIO_ESPECIAL = "PRECIO_ESPECIAL"
MULTIPLICADOR_PUNTOS = "MULTIPLICADOR_PUNTOS"
CUPON_UNICO = "CUPON_UNICO"
COMBO = "COMBO"

# Mecánicas cuyo beneficio depende de la cantidad de unidades: no se proponen solas.
REQUIERE_CANTIDAD: frozenset[str] = frozenset({DOS_POR_UNO, COMBO})


def requiere_cantidad(mecanica: str) -> bool:
    return mecanica in REQUIERE_CANTIDAD


def calcular_descuento(mecanica: str, valor: int, monto: int) -> int:
    """Descuento en pesos (enteros) para un `monto` dado. Nunca mayor que el monto."""
    if monto <= 0:
        return 0
    if mecanica in (PORCENTAJE, CUPON_UNICO):
        return min(monto, monto * valor // 100)
    if mecanica == MONTO_FIJO:
        return min(valor, monto)
    if mecanica in (PRECIO_ESPECIAL, COMBO):
        # valor = precio final; el descuento es lo que se ahorra respecto del monto.
        return max(0, monto - valor)
    if mecanica == DOS_POR_UNO:
        # Aproximación para mostrar: se paga la mitad (dos unidades iguales). Manual.
        return monto // 2
    # MULTIPLICADOR_PUNTOS: beneficio en puntos (módulo puntos, después): no descuenta pesos.
    return 0
