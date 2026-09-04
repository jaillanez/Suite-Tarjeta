"""Tipos del módulo contenido (§11)."""

from __future__ import annotations

from enum import StrEnum


class OrigenPieza(StrEnum):
    FOTO_PROPIA = "FOTO_PROPIA"  # el camino recomendado: foto real del comercio (§11.7)
    IA = "IA"  # fondo generado por IA cuando no hay foto disponible


class EstadoPieza(StrEnum):
    BORRADOR = "BORRADOR"
    EN_MODERACION = "EN_MODERACION"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class FormatoPieza(StrEnum):
    CUADRADO = "CUADRADO"  # feed
    VERTICAL = "VERTICAL"  # historias
    HORIZONTAL = "HORIZONTAL"  # banner de la app


# Tamaños de salida (§11.8): los tres formatos derivados de cada pieza.
TAMANOS: dict[FormatoPieza, tuple[int, int]] = {
    FormatoPieza.CUADRADO: (1080, 1080),
    FormatoPieza.VERTICAL: (1080, 1920),
    FormatoPieza.HORIZONTAL: (1200, 628),
}
