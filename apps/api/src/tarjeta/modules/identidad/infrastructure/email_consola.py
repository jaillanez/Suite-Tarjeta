"""Adaptador de email de desarrollo: escribe el mensaje en el log.

Deshabilitado fuera de `dev`: en cualquier otro entorno lanza RuntimeError (en prod, la guarda de
arranque ya obliga a configurar un proveedor real). Cuando exista el proveedor real, se agrega un
adaptador `EmailReal` y se cablea en `composition.py` según `settings.email_proveedor`.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("identidad.email")


class EmailConsola:
    def __init__(self, *, environment: str) -> None:
        self._environment = environment

    async def enviar(self, email: str, asunto: str, cuerpo: str) -> None:
        if self._environment != "dev":
            raise RuntimeError("El adaptador de email por consola solo puede usarse en dev.")
        _log.info("EMAIL de desarrollo a %s | %s | %s", email, asunto, cuerpo)
