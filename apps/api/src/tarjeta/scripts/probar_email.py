"""Envía un correo de prueba con el proveedor configurado (§15.2) y reporta el resultado.

Uso:  uv run python -m tarjeta.scripts.probar_email destino@ejemplo.com [ruta_env]

Carga `config/produccion.env` (o el archivo indicado) en el entorno, construye el emisor según la
configuración y envía un correo de prueba. Con `TARJETA_EMAIL_PROVEEDOR=real` sale por SMTP; en
`consola` (dev) se escribe al log en vez de enviarse.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from tarjeta.config import API_ROOT, get_settings
from tarjeta.modules.identidad.infrastructure.composition import _emisor_email

_DEFECTO = API_ROOT.parents[1] / "config" / "produccion.env"


def _cargar_env(ruta: Path) -> None:
    if not ruta.exists():
        return
    for linea in ruta.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ[clave.strip()] = valor.strip()


async def _enviar(destino: str) -> str:
    settings = get_settings()
    emisor = _emisor_email(settings)
    await emisor.enviar(
        destino,
        "Prueba de correo — Tarjeta de Beneficios",
        "Este es un correo de prueba del sistema (§15.2). Si lo recibiste, el envío funciona.",
    )
    return type(emisor).__name__


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: probar_email destino@ejemplo.com [ruta_env]")
        sys.exit(2)
    destino = sys.argv[1]
    ruta = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFECTO
    _cargar_env(ruta)
    get_settings.cache_clear()
    try:
        adaptador = asyncio.run(_enviar(destino))
    except Exception as exc:  # noqa: BLE001 - reportar cualquier fallo de SMTP con claridad
        print(f"✗ Falló el envío a {destino}: {type(exc).__name__}: {exc}")
        sys.exit(1)
    if adaptador == "EmailConsola":
        print(f"⚠ Modo consola (dev): el correo a {destino} se escribió al log, no se envió.")
        print("  Configurá TARJETA_EMAIL_PROVEEDOR=real y los datos SMTP para enviar de verdad.")
    else:
        print(f"✓ Correo de prueba enviado a {destino} vía SMTP.")


if __name__ == "__main__":
    main()
