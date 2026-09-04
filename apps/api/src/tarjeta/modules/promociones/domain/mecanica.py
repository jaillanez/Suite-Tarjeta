"""Mecánicas y segmentación de una promoción (§1.6, §07.2)."""

from __future__ import annotations

from enum import StrEnum


class Mecanica(StrEnum):
    PORCENTAJE = "PORCENTAJE"  # valor = % de descuento
    MONTO_FIJO = "MONTO_FIJO"  # valor = monto en pesos
    DOS_POR_UNO = "DOS_POR_UNO"  # valor ignorado
    PRECIO_ESPECIAL = "PRECIO_ESPECIAL"  # valor = precio final
    MULTIPLICADOR_PUNTOS = "MULTIPLICADOR_PUNTOS"  # valor = multiplicador (x100, ej 200 = 2x)
    CUPON_UNICO = "CUPON_UNICO"  # valor = % o monto según se configure; un uso por persona
    COMBO = "COMBO"  # valor = precio del combo


class Segmento(StrEnum):
    """A quién alcanza la promoción por nivel (§07.2, conversión fiscal)."""

    AMBOS = "AMBOS"  # Platino y Black, con valores diferenciados
    SOLO_BLACK = "SOLO_BLACK"  # exclusiva Black (los Platino la ven bloqueada en el feed)


# Mecánicas donde el "valor" mayor significa MÁS beneficio para el ciudadano.
# Para PRECIO_ESPECIAL/COMBO el valor es un precio: menor es mejor, pero no se comparan por
# valor crudo (el motor usa `beneficio_relativo`).
_MAYOR_ES_MEJOR = {
    Mecanica.PORCENTAJE,
    Mecanica.MONTO_FIJO,
    Mecanica.MULTIPLICADOR_PUNTOS,
}


def beneficio_relativo(mecanica: Mecanica, valor: int) -> float:
    """Puntaje comparable de beneficio para ordenar (mayor = mejor para el ciudadano).

    Es una heurística para el motor de resolución; el detalle económico exacto lo calcula el
    canje. 2x1 se pondera alto; precio especial/combo se ordenan por conveniencia inversa.
    """
    if mecanica in _MAYOR_ES_MEJOR:
        return float(valor)
    if mecanica is Mecanica.DOS_POR_UNO:
        return 50.0  # equivalente aproximado a 50% en la práctica
    if mecanica in (Mecanica.PRECIO_ESPECIAL, Mecanica.COMBO):
        # Un precio más bajo es mejor; se invierte para que "mayor = mejor".
        return 1.0 / valor if valor > 0 else 0.0
    if mecanica is Mecanica.CUPON_UNICO:
        return float(valor)
    return 0.0
