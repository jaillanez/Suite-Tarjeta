"""Niveles de ciudadano (§3.2). Platino es base; Black es de quien está al día."""

from __future__ import annotations

from enum import StrEnum


class Nivel(StrEnum):
    PLATINO = "PLATINO"
    BLACK = "BLACK"


class NivelOrigen(StrEnum):
    PROPIO = "PROPIO"
    HEREDADO_GRUPO = "HEREDADO_GRUPO"


def calcular_nivel(*, al_dia: bool, excepcion_black_vigente: bool) -> Nivel:
    """BLACK si está al día (o hay excepción vigente); PLATINO en cualquier otro caso."""
    if al_dia or excepcion_black_vigente:
        return Nivel.BLACK
    return Nivel.PLATINO


# Snapshot textual de la regla, guardado en el histórico (no una referencia mutable).
REGLA_VIGENTE = "BLACK si al_dia=true o excepcion_black vigente; PLATINO en otro caso (v2.1)"
