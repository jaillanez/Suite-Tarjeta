"""Implementación de prueba del verificador de identidad (RENAPER).

Devuelve un resultado configurable. La integración real llega más adelante.
"""

from __future__ import annotations

from tarjeta.modules.identidad.domain.ports import ResultadoVerificacion


class RenaperStub:
    def __init__(self, *, resultado: str = "aprobado") -> None:
        self._resultado = resultado

    async def verificar(self, *, dni: str, cuil: str) -> ResultadoVerificacion:
        if self._resultado == "aprobado":
            return ResultadoVerificacion(aprobado=True, requiere_revision=False, metodo="RENAPER")
        if self._resultado == "revision":
            return ResultadoVerificacion(aprobado=False, requiere_revision=True, metodo="RENAPER")
        return ResultadoVerificacion(aprobado=False, requiere_revision=False, metodo="RENAPER")
