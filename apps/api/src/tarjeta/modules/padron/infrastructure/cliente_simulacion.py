"""Adaptador de simulación del padrón (§13.1).

Lee las respuestas de un archivo **YAML** configurable por DNI/CUIT. Cualquier DNI/CUIT que no
figure devuelve `False` (no hay regla por paridad ni ninguna otra heurística). Recarga en caliente:
si el archivo cambia en disco, la próxima consulta usa los datos nuevos, sin reiniciar la app.

Formato (ver `datos/padron.yaml`):

    contribuyentes:
      - dni: "20123456"
        al_dia: true
    comercios:
      - cuit: "30712345678"
        es_comerciante: true
    caidos: ["11111111"]   # opcional: DNIs/CUITs que simulan el endpoint caído

El adaptador real (`cliente_real.py`) queda intacto: pasar a modo real es sólo configuración
(`TARJETA_PADRON_MODO=real`). En prod, la guarda de arranque impide arrancar en simulación.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tarjeta.modules.padron.domain.errors import PadronNoDisponible


def _norm_dni(dni: str) -> str:
    return dni.strip()


def _norm_cuit(cuit: str) -> str:
    return "".join(c for c in cuit if c.isdigit())


class ClientePadronSimulado:
    def __init__(
        self,
        *,
        al_dia_por_dni: dict[str, bool] | None = None,
        comerciante_por_cuit: dict[str, bool] | None = None,
        caidos: set[str] | None = None,
        ruta: Path | None = None,
    ) -> None:
        self._al_dia = {_norm_dni(k): v for k, v in (al_dia_por_dni or {}).items()}
        self._comerciante = {_norm_cuit(k): v for k, v in (comerciante_por_cuit or {}).items()}
        self._caidos = set(caidos or set())
        self._ruta = ruta
        self._mtime: float | None = None
        if ruta is not None:
            self._recargar_si_cambio()

    @classmethod
    def desde_archivo(cls, ruta: str) -> ClientePadronSimulado:
        return cls(ruta=Path(ruta)) if ruta else cls()

    def _recargar_si_cambio(self) -> None:
        if self._ruta is None or not self._ruta.exists():
            return
        mtime = self._ruta.stat().st_mtime
        if mtime == self._mtime:
            return
        self._mtime = mtime
        data = yaml.safe_load(self._ruta.read_text()) or {}
        self._al_dia = {
            _norm_dni(str(c["dni"])): bool(c.get("al_dia", False))
            for c in data.get("contribuyentes", [])
        }
        self._comerciante = {
            _norm_cuit(str(c["cuit"])): bool(c.get("es_comerciante", False))
            for c in data.get("comercios", [])
        }
        self._caidos = {str(x) for x in data.get("caidos", [])}

    def _esta_caido(self, *candidatos: str) -> bool:
        return any(c in self._caidos for c in candidatos)

    async def al_dia(self, dni: str) -> bool:
        self._recargar_si_cambio()
        if self._esta_caido(dni.strip()):
            raise PadronNoDisponible("Simulación: endpoint caído.")
        return self._al_dia.get(_norm_dni(dni), False)

    async def es_comerciante(self, cuit: str) -> bool:
        self._recargar_si_cambio()
        if self._esta_caido(cuit, _norm_cuit(cuit)):
            raise PadronNoDisponible("Simulación: endpoint caído.")
        return self._comerciante.get(_norm_cuit(cuit), False)
