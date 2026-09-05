"""Integración (§13.2): los tres textos legales quedaron cargados, versionados y vigentes,
con la nota de revisión legal visible en el propio texto."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402

_NOTA = "No utilizar sin revisión legal"
_TIPOS = ("TERMINOS_CIUDADANO", "PRIVACIDAD", "CONVENIO_COMERCIO")


async def test_textos_legales_cargados_con_nota() -> None:
    engine = create_async_engine(str(get_settings().database_url))
    try:
        async with engine.connect() as conn:
            filas = (
                await conn.execute(
                    text(
                        "SELECT tipo, version, vigente, texto FROM texto_legal "
                        "WHERE tipo = ANY(:tipos)"
                    ),
                    {"tipos": list(_TIPOS)},
                )
            ).all()
    except Exception as exc:  # noqa: BLE001 - base no disponible en local
        await engine.dispose()
        pytest.skip(f"Base no disponible: {exc}")
    finally:
        await engine.dispose()

    por_tipo = {f.tipo: f for f in filas}
    for tipo in _TIPOS:
        assert tipo in por_tipo, f"falta el texto legal {tipo}"
        fila = por_tipo[tipo]
        assert fila.version == "v1"
        assert fila.vigente is True
        assert _NOTA in fila.texto, f"la nota de revisión legal no está en {tipo}"
