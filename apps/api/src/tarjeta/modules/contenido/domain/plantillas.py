"""Plantillas de marca del programa (§11.7).

Cada plantilla sirve para los tres formatos, así que estas ocho cubren de sobra el mínimo de seis
por formato. Definen paleta y estilo; el espacio del logo del comercio y del isologo municipal lo
resuelve el compositor. Salen de acá (no se escriben en el compositor) para poder crecer sin tocar
código de render.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Plantilla:
    id: str
    nombre: str
    color_fondo: str  # hex, si la pieza no trae fondo propio/IA
    color_texto: str
    color_acento: str
    estilo: str  # descripción para el prompt de IA


PLANTILLAS: tuple[Plantilla, ...] = (
    Plantilla(
        "clasica", "Clásica", "#0B3D91", "#FFFFFF", "#F2A900", "sobrio, institucional, limpio"
    ),
    Plantilla("calida", "Cálida", "#7A1F1F", "#FFF7EC", "#F2A900", "cálido, cercano, artesanal"),
    Plantilla("fresca", "Fresca", "#0E6E4E", "#FFFFFF", "#B7E4C7", "fresco, natural, verde"),
    Plantilla(
        "nocturna", "Nocturna", "#111827", "#F9FAFB", "#8B5CF6", "elegante, oscuro, nocturno"
    ),
    Plantilla("pastel", "Pastel", "#FCE7F3", "#3F3F46", "#F472B6", "suave, pastel, amable"),
    Plantilla("cítrica", "Cítrica", "#F59E0B", "#3F2D00", "#FDE68A", "vibrante, cítrico, alegre"),
    Plantilla("marina", "Marina", "#075985", "#F0F9FF", "#38BDF8", "marino, celeste, aireado"),
    Plantilla("tierra", "Tierra", "#5B3A1B", "#FBF3E4", "#D9A066", "terroso, natural, rústico"),
)

_POR_ID = {p.id: p for p in PLANTILLAS}
PLANTILLA_POR_DEFECTO = PLANTILLAS[0].id


def obtener_plantilla(id_plantilla: str) -> Plantilla:
    return _POR_ID.get(id_plantilla, PLANTILLAS[0])
