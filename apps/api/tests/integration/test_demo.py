"""Integración (§13.5): el modo demostración deja el escenario completo con un comando y es
idempotente (re-ejecutar restablece el mismo estado, sin duplicar el libro append-only)."""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.scripts import demo  # noqa: E402
from tarjeta.scripts.cargar_comercios import _id as _id_comercio  # noqa: E402

_BLACK = demo._did("persona", "20111222")
_PLATINO = demo._did("persona", "27333444")
_CAJERO = demo._did("persona", "23555666")
_COMERCIO = _id_comercio("comercio", demo._CUIT_DEMO)
_USUARIO = demo._did("usuario", demo._CUIT_DEMO, str(_CAJERO))
_BILLETERA = demo._did("billetera", str(_BLACK), demo._CUIT_DEMO)
_GRUPO = demo._did("grupo", str(_BLACK))


async def test_demo_idempotente_y_escenario_completo() -> None:
    engine = create_async_engine(str(get_settings().database_url))
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - base no disponible en local
        await engine.dispose()
        pytest.skip(f"Base no disponible: {exc}")

    # Un comando, dos veces: idempotente.
    await demo._sembrar()
    await demo._sembrar()

    async with engine.connect() as conn:

        async def scalar(q: str, **p: object) -> object:
            return (await conn.execute(text(q), p)).scalar_one()

        niveles = dict(
            (r.id_persona, r.nivel)
            for r in (
                await conn.execute(
                    text(
                        "SELECT id_persona, nivel FROM perfil_ciudadano WHERE id_persona = ANY(:i)"
                    ),
                    {"i": [_BLACK, _PLATINO]},
                )
            ).all()
        )
        assert niveles[_BLACK] == "BLACK"
        assert niveles[_PLATINO] == "PLATINO"

        # Comercio con cajero y turno abierto.
        assert (
            await scalar(
                "SELECT count(*) FROM turno_comercio WHERE id_cajero = :u AND cerrado_en IS NULL",
                u=_USUARIO,
            )
            == 1
        )
        assert (
            await scalar(
                "SELECT count(*) FROM usuario_comercio WHERE id = :u AND rol = 'CAJERO'", u=_USUARIO
            )
            == 1
        )

        # Promos de distintas mecánicas, activas.
        assert (
            await scalar(
                "SELECT count(distinct mecanica) FROM promocion "
                "WHERE id_comercio = :c AND estado = 'ACTIVA'",
                c=_COMERCIO,
            )
            >= 3
        )

        # Grupo familiar: titular + miembro activos.
        assert (
            await scalar(
                "SELECT count(*) FROM miembro_grupo WHERE id_grupo = :g AND estado = 'ACTIVO'",
                g=_GRUPO,
            )
            == 2
        )

        # Puntos: saldo y movimientos (append-only) sin duplicar tras la 2da corrida.
        assert await scalar("SELECT saldo FROM billetera WHERE id = :b", b=_BILLETERA) == 500
        movs = (
            await conn.execute(
                text(
                    "SELECT count(*), coalesce(sum(monto), 0) FROM movimiento_billetera "
                    "WHERE id_billetera = :b"
                ),
                {"b": _BILLETERA},
            )
        ).one()
        assert movs[0] == 2  # idempotente: no se duplicó el libro
        assert movs[1] == 500

        # Credenciales para poder iniciar sesión en la demo.
        assert (
            await scalar(
                "SELECT count(*) FROM credencial WHERE id_persona = ANY(:i)",
                i=[_BLACK, _PLATINO, _CAJERO],
            )
            == 3
        )

    await engine.dispose()


def test_ids_demo_son_uuid() -> None:
    # Los ids deterministas son UUID válidos (el namespace de la demo es estable).
    assert isinstance(_BLACK, uuid.UUID)
    assert _BLACK != _PLATINO
