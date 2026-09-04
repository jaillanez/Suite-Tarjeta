"""Almacén de objetos local (§11.10): adaptador de desarrollo detrás del puerto AlmacenObjetos.

Las imágenes se sirven como archivos estáticos con caché larga (igual que los tiles). En producción
se reemplaza por un bucket sin tocar el resto del código.
"""

from __future__ import annotations

from pathlib import Path


class AlmacenLocal:
    def __init__(self, base_dir: str, *, url_prefijo: str = "/contenido") -> None:
        self._base = Path(base_dir)
        self._prefijo = url_prefijo.rstrip("/")
        self._base.mkdir(parents=True, exist_ok=True)

    def _ruta(self, clave: str) -> Path:
        return self._base / clave

    async def guardar(self, clave: str, datos: bytes, content_type: str) -> None:
        ruta = self._ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(datos)

    async def leer(self, clave: str) -> bytes | None:
        ruta = self._ruta(clave)
        return ruta.read_bytes() if ruta.exists() else None

    async def borrar(self, clave: str) -> None:
        ruta = self._ruta(clave)
        if ruta.exists():
            ruta.unlink()

    def url_publica(self, clave: str) -> str:
        return f"{self._prefijo}/{clave}"
