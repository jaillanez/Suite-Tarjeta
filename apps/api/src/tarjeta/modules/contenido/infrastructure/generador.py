"""Adaptadores del puerto GeneradorImagen (§11.2).

Simulación: imágenes de prueba deterministas, sin red ni gasto (dev y tests). Real: detrás del
mismo puerto, exige configuración explícita (no se puede activar sin API key). No se elige el
proveedor acá: la llamada concreta queda para cuando el municipio elija uno.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image

from tarjeta.modules.contenido.domain.errors import ProveedorNoConfigurado


def _parse_tamano(tamano: str) -> tuple[int, int]:
    try:
        w, h = tamano.lower().split("x", 1)
        return (int(w), int(h))
    except ValueError:
        return (1024, 1024)


def _color_determinista(semilla: str) -> tuple[int, int, int]:
    d = hashlib.md5(semilla.encode()).digest()
    return (d[0], d[1], d[2])


def _png_solido(ancho: int, alto: int, color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buf, format="PNG")
    return buf.getvalue()


class GeneradorSimulacion:
    """Devuelve fondos de color determinista según el prompt. No llama a ningún servicio."""

    nombre = "simulacion"

    async def generar(self, prompt: str, *, cantidad: int, tamano: str) -> list[bytes]:
        ancho, alto = _parse_tamano(tamano)
        return [
            _png_solido(ancho, alto, _color_determinista(f"{prompt}::{i}"))
            for i in range(max(1, cantidad))
        ]


class GeneradorReal:
    """Adaptador real: exige API key. La integración con el proveedor elegido va después."""

    def __init__(self, *, api_key: str, modelo: str, base_url: str) -> None:
        if not api_key or not base_url:
            raise ProveedorNoConfigurado(
                "El generador real necesita API key y endpoint configurados."
            )
        self.nombre = modelo or "real"
        self._api_key = api_key
        self._base_url = base_url

    async def generar(self, prompt: str, *, cantidad: int, tamano: str) -> list[bytes]:
        # No se elige el proveedor por nuestra cuenta (§11.2): cuando el municipio elija uno, la
        # llamada HTTP concreta se implementa acá, detrás de este mismo puerto.
        raise NotImplementedError(
            "Falta integrar el proveedor de imágenes elegido por el municipio."
        )
