"""Verifica la configuración de producción (§15.1).

Revisa que estén TODAS las claves requeridas en `config/produccion.env` (o el archivo indicado) y
avisa cuáles faltan o están vacías. **Nunca imprime los valores** (son secretos): solo los nombres
de las claves y si están presentes.

Uso:  uv run python -m tarjeta.scripts.verificar_config [ruta_env]
"""

from __future__ import annotations

import sys
from pathlib import Path

from tarjeta.config import API_ROOT

_REPO_ROOT = API_ROOT.parents[1]
_DEFECTO = _REPO_ROOT / "config" / "produccion.env"

# Claves que deben estar presentes y no vacías para poder arrancar en producción.
_REQUERIDAS = (
    "TARJETA_ENVIRONMENT",
    "TARJETA_DATABASE_URL",
    "TARJETA_DATABASE_MIGRATOR_URL",
    "TARJETA_REDIS_URL",
    "TARJETA_PADRON_BASE_URL",
    "TARJETA_PADRON_API_KEY",
    "TARJETA_JWT_SECRET",
    "TARJETA_FIELD_ENCRYPTION_KEY",
    "TARJETA_FIELD_PEPPER",
    "TARJETA_EMAIL_SMTP_HOST",
    "TARJETA_EMAIL_SMTP_PORT",
    "TARJETA_EMAIL_SMTP_USER",
    "TARJETA_EMAIL_SMTP_PASSWORD",
    "TARJETA_EMAIL_FROM",
    "NEXT_PUBLIC_TILES_URL",
)
# Marcadores de valor "sin completar" que cuentan como faltantes.
_SIN_COMPLETAR = ("cambiar", "reemplazar", "changeme")


def _parsear(ruta: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linea in ruta.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        valores[clave.strip()] = valor.strip()
    return valores


def main() -> None:
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFECTO
    if not ruta.exists():
        print(f"✗ No existe {ruta}. Copiá config/produccion.env.ejemplo y completalo.")
        sys.exit(1)

    valores = _parsear(ruta)
    faltan: list[str] = []
    sin_completar: list[str] = []
    for clave in _REQUERIDAS:
        v = valores.get(clave, "")
        if not v:
            faltan.append(clave)
        elif any(m in v.lower() for m in _SIN_COMPLETAR):
            sin_completar.append(clave)

    presentes = len(_REQUERIDAS) - len(faltan) - len(sin_completar)
    print(f"Config: {ruta}")
    print(f"Claves OK: {presentes}/{len(_REQUERIDAS)}")
    for clave in faltan:
        print(f"  ✗ falta: {clave}")
    for clave in sin_completar:
        print(f"  ✗ sin completar (valor de ejemplo): {clave}")
    if faltan or sin_completar:
        print("Completá esas claves antes de desplegar. (No se muestran valores por seguridad.)")
        sys.exit(1)
    print("✓ Todas las claves requeridas están presentes.")


if __name__ == "__main__":
    main()
