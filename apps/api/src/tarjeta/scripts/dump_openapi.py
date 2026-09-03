"""Vuelca el esquema OpenAPI de la API a un archivo JSON (§06.0.A).

El cliente TypeScript (`packages/api-client/schema.generated.ts`) se genera desde este JSON.
El CI corre este script + la generación del cliente y falla si algo quedó desactualizado, de
modo que el contrato del backend y los tipos del frontend no puedan divergir en silencio.

Uso:  uv run python -m tarjeta.scripts.dump_openapi [ruta_salida]
Por defecto escribe packages/api-client/openapi.json (relativo a la raíz del repo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tarjeta.main import create_app

# apps/api/src/tarjeta/scripts/dump_openapi.py -> raíz del repo (../../../../..)
_RAIZ = Path(__file__).resolve().parents[5]
_DESTINO_POR_DEFECTO = _RAIZ / "packages" / "api-client" / "openapi.json"


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else _DESTINO_POR_DEFECTO
    esquema = create_app().openapi()
    destino.write_text(json.dumps(esquema, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"OpenAPI escrito en {destino}")


if __name__ == "__main__":
    main()
