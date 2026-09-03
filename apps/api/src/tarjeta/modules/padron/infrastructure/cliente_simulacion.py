"""Adaptador de simulación del padrón para desarrollo y tests.

Respuestas configurables por DNI/CUIT desde un archivo JSON, con una regla determinística
por defecto para los no listados. Permite simular: al día, en mora / no contribuyente,
comerciante, y caída del endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

from tarjeta.modules.padron.domain.errors import PadronNoDisponible


class ClientePadronSimulado:
    def __init__(
        self,
        *,
        al_dia_por_dni: dict[str, bool] | None = None,
        comerciante_por_cuit: dict[str, bool] | None = None,
        caidos: set[str] | None = None,
    ) -> None:
        self._al_dia = al_dia_por_dni or {}
        self._comerciante = comerciante_por_cuit or {}
        self._caidos = caidos or set()

    @classmethod
    def desde_archivo(cls, ruta: str) -> ClientePadronSimulado:
        if not ruta or not Path(ruta).exists():
            return cls()
        data = json.loads(Path(ruta).read_text())
        return cls(
            al_dia_por_dni=data.get("al_dia", {}),
            comerciante_por_cuit=data.get("es_comerciante", {}),
            caidos=set(data.get("caidos", [])),
        )

    async def al_dia(self, dni: str) -> bool:
        if dni in self._caidos:
            raise PadronNoDisponible("Simulación: endpoint caído.")
        if dni in self._al_dia:
            return self._al_dia[dni]
        # Regla por defecto determinística: DNI par => al día. Útil y predecible en tests.
        return int(dni) % 2 == 0 if dni.isdigit() else False

    async def es_comerciante(self, cuit: str) -> bool:
        return self._comerciante.get(cuit, False)
