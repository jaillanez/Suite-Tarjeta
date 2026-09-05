"""Integración (§13.3): la carga de comercios de precarga es idempotente, deja todo ACTIVA con
promos activas y bandera de precarga, y se puede dar de baja en bloque."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from tarjeta.config import get_settings  # noqa: E402
from tarjeta.scripts.baja_precarga import _baja  # noqa: E402
from tarjeta.scripts.cargar_comercios import _cargar  # noqa: E402

_DATASET = [
    {
        "cuit": "30999000011",
        "razon_social": "Prueba Uno SRL",
        "nombre_fantasia": "Comercio Prueba Uno",
        "rubro": "kiosco",
        "origen": "test (2026-09-05)",
        "sucursal": {
            "nombre": "Casa Central",
            "direccion": "Calle Falsa 123, Rivadavia",
            "telefono": "264 4000001",
            "lat": -31.5355,
            "lon": -68.5990,
            "horarios": [{"dia": 0, "franjas": [{"desde": "09:00", "hasta": "18:00"}]}],
        },
        "promociones": [
            {
                "titulo": "10% test",
                "mecanica": "PORCENTAJE",
                "segmento": "AMBOS",
                "valor_platino": 10,
                "valor_black": 15,
            },
        ],
    },
    {
        "cuit": "30999000029",
        "razon_social": "Prueba Dos SRL",
        "nombre_fantasia": "Comercio Prueba Dos",
        "rubro": "panaderia",
        "origen": "test (2026-09-05)",
        "sucursal": {
            "nombre": "Casa Central",
            "direccion": "Av. Siempreviva 742, Rivadavia",
            "telefono": "264 4000002",
            "lat": -31.5405,
            "lon": -68.6180,
            "horarios": [{"dia": 1, "franjas": [{"desde": "08:00", "hasta": "13:00"}]}],
        },
        "promociones": [
            {
                "titulo": "2x1 test",
                "mecanica": "DOS_POR_UNO",
                "segmento": "SOLO_BLACK",
                "valor_black": 0,
            },
        ],
    },
]
_CUITS = tuple(c["cuit"] for c in _DATASET)


async def _contar(engine, estado: str | None = None) -> int:
    q = "SELECT count(*) FROM comercio WHERE cuit = ANY(:cuits)"
    params: dict[str, object] = {"cuits": list(_CUITS)}
    if estado is not None:
        q += " AND estado = :estado"
        params["estado"] = estado
    async with engine.connect() as conn:
        return int((await conn.execute(text(q), params)).scalar_one())


async def test_carga_idempotente_y_baja_en_bloque() -> None:
    engine = create_async_engine(str(get_settings().database_url))
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - base no disponible en local
        await engine.dispose()
        pytest.skip(f"Base no disponible: {exc}")

    try:
        await _cargar(_DATASET)
        await _cargar(_DATASET)  # idempotente: no duplica
        assert await _contar(engine) == 2
        assert await _contar(engine, "ACTIVA") == 2

        async with engine.connect() as conn:
            # precarga + origen guardados
            filas = (
                await conn.execute(
                    text("SELECT precarga, origen FROM comercio WHERE cuit = ANY(:c)"),
                    {"c": list(_CUITS)},
                )
            ).all()
            assert all(f.precarga is True and f.origen for f in filas)
            # una sucursal por comercio, con lat/lon derivadas
            sucs = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM sucursal s JOIN comercio c ON c.id = s.id_comercio "
                        "WHERE c.cuit = ANY(:c) AND s.lat IS NOT NULL"
                    ),
                    {"c": list(_CUITS)},
                )
            ).scalar_one()
            assert sucs == 2
            # promos activas
            promos = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM promocion p JOIN comercio c ON c.id = p.id_comercio "
                        "WHERE c.cuit = ANY(:c) AND p.estado = 'ACTIVA'"
                    ),
                    {"c": list(_CUITS)},
                )
            ).scalar_one()
            assert promos == 2

        # Baja en bloque: los de precarga quedan en BAJA (afecta a estos 2 y a otros precargados).
        await _baja()
        assert await _contar(engine, "ACTIVA") == 0
        assert await _contar(engine, "BAJA") == 2
    finally:
        # Limpieza: dejar la base sin estos comercios de prueba.
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "DELETE FROM promocion_sucursal WHERE id_sucursal IN "
                    "(SELECT s.id FROM sucursal s JOIN comercio c ON c.id = s.id_comercio "
                    "WHERE c.cuit = ANY(:c))"
                ),
                {"c": list(_CUITS)},
            )
            await conn.execute(
                text(
                    "DELETE FROM promocion WHERE id_comercio IN "
                    "(SELECT id FROM comercio WHERE cuit = ANY(:c))"
                ),
                {"c": list(_CUITS)},
            )
            await conn.execute(
                text(
                    "DELETE FROM sucursal WHERE id_comercio IN "
                    "(SELECT id FROM comercio WHERE cuit = ANY(:c))"
                ),
                {"c": list(_CUITS)},
            )
            await conn.execute(
                text("DELETE FROM comercio WHERE cuit = ANY(:c)"), {"c": list(_CUITS)}
            )
        await engine.dispose()
