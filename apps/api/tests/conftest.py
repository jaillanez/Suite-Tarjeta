"""Configuración común de pytest.

§13.1: el padrón simulado lee de un YAML (sin paridad de DNI). Para los tests, la fixture autouse
`_padron_tmp` apunta `TARJETA_PADRON_SIM_ARCHIVO` a un YAML temporal por test y limpia el cache de
`get_settings`, de modo que **ambos seams** del padrón lo usen: el de registro (`al_dia`, vía
`create_app()` → dispatcher) y el de adhesión de comercios (`es_comerciante`, vía `get_settings()`
en la request). La fixture `padron` siembra valores; la recarga en caliente del simulador los toma.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from tarjeta.config import get_settings


@pytest.fixture(autouse=True)
def _padron_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    archivo = tmp_path / "padron.yaml"
    archivo.write_text("contribuyentes: []\ncomercios: []\ncaidos: []\n")
    monkeypatch.setenv("TARJETA_PADRON_SIM_ARCHIVO", str(archivo))
    get_settings.cache_clear()
    yield archivo
    get_settings.cache_clear()


class _SeedPadron:
    """Siembra el YAML del padrón; la recarga en caliente lo toma en la próxima consulta."""

    def __init__(self, archivo: Path) -> None:
        self._archivo = archivo

    def _data(self) -> dict[str, list[object]]:
        return yaml.safe_load(self._archivo.read_text()) or {
            "contribuyentes": [],
            "comercios": [],
            "caidos": [],
        }

    def _write(self, data: dict[str, list[object]]) -> None:
        self._archivo.write_text(yaml.safe_dump(data))

    def al_dia(self, dni: str, valor: bool = True) -> None:
        data = self._data()
        data.setdefault("contribuyentes", []).append({"dni": str(dni), "al_dia": valor})
        self._write(data)

    def comerciante(self, cuit: str, valor: bool = True) -> None:
        data = self._data()
        data.setdefault("comercios", []).append({"cuit": str(cuit), "es_comerciante": valor})
        self._write(data)

    def caido(self, clave: str) -> None:
        data = self._data()
        data.setdefault("caidos", []).append(str(clave))
        self._write(data)


@pytest.fixture
def padron(_padron_tmp: Path) -> _SeedPadron:
    return _SeedPadron(_padron_tmp)
