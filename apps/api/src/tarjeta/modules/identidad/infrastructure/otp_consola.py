"""Adaptador de OTP de desarrollo: escribe el código en el log.

Deshabilitado fuera de `dev` (§03.6): en cualquier otro entorno lanza RuntimeError.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("identidad.otp")


class OtpConsola:
    def __init__(self, *, environment: str) -> None:
        self._environment = environment

    async def enviar(self, celular: str, codigo: str) -> None:
        if self._environment != "dev":
            raise RuntimeError("El adaptador de OTP por consola solo puede usarse en dev.")
        _log.info("OTP de desarrollo para %s: %s", celular, codigo)
