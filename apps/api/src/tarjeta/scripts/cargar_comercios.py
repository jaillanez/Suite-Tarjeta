"""Carga idempotente de comercios de precarga (§13.3).

Lee un archivo YAML versionado (por defecto `datos/comercios_rivadavia.yaml`) y siembra los
comercios con su sucursal y sus promociones, todos en estado ACTIVA y marcados como **precarga**
(bandera para identificarlos y darlos de baja en bloque; ver `baja_precarga.py`). Guarda el
**origen** del dato (de dónde salió y cuándo) para el promotor que después los visite.

Es idempotente: los ids se derivan de claves naturales (uuid5), así que correrlo dos veces
actualiza en lugar de duplicar. No pasa por la máquina de adhesión: crea los comercios ya activos
para poder probar el sistema completo. La validación fiscal, si se corriera, pasa porque el padrón
simulado marca sus CUIT como inscriptos (ver `datos/padron.yaml`).

Uso:  uv run python -m tarjeta.scripts.cargar_comercios [ruta_yaml]
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from tarjeta.config import API_ROOT
from tarjeta.modules.comercios.infrastructure.models import ComercioModel, SucursalModel
from tarjeta.modules.comercios.infrastructure.repositories import _punto
from tarjeta.modules.promociones.infrastructure.models import (
    PromocionModel,
    PromocionSucursalModel,
)
from tarjeta.shared.infrastructure.database import get_sessionmaker

_NS = uuid.UUID("6f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b")  # namespace estable de la precarga
_VIGENCIA_DESDE = date(2026, 1, 1)
_VIGENCIA_HASTA = date(2027, 12, 31)
_RUTA_DEFECTO = API_ROOT / "datos" / "comercios_rivadavia.yaml"


def _id(*partes: str) -> uuid.UUID:
    return uuid.uuid5(_NS, "|".join(partes))


async def _cargar(datos: list[dict[str, Any]]) -> int:
    ahora = datetime.now(UTC)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as s:
        for c in datos:
            cuit = str(c["cuit"])
            id_com = _id("comercio", cuit)
            com = await s.get(ComercioModel, id_com)
            if com is None:
                com = ComercioModel(id=id_com, cuit=cuit, creado_en=ahora)
                s.add(com)
            com.razon_social = c["razon_social"]
            com.nombre_fantasia = c.get("nombre_fantasia", "")
            com.rubro = c.get("rubro", "")
            com.logo_url = c.get("logo_url", "")
            com.id_responsable = _id("responsable", cuit)
            com.estado = "ACTIVA"
            com.convenio_version = "precarga"
            com.convenio_fecha = ahora
            com.convenio_ip = "0.0.0.0"
            com.precarga = True
            com.origen = c.get("origen", "precarga")

            suc = c["sucursal"]
            id_suc = _id("sucursal", cuit, suc["nombre"])
            sm = await s.get(SucursalModel, id_suc)
            if sm is None:
                sm = SucursalModel(id=id_suc, id_comercio=id_com)
                s.add(sm)
            sm.nombre = suc["nombre"]
            sm.direccion = suc.get("direccion", "")
            sm.telefono = suc.get("telefono", "")
            # `ubicacion` es la fuente de verdad; un trigger deriva lat/lon (§07.0.B).
            sm.ubicacion = _punto(float(suc["lat"]), float(suc["lon"]))
            sm.estado = "ACTIVA"
            sm.es_casa_central = True
            sm.horarios = suc.get("horarios", [])
            sm.fotos = []
            sm.qr_token = ""

            for promo in c.get("promociones", []):
                id_promo = _id("promocion", cuit, promo["titulo"])
                pm = await s.get(PromocionModel, id_promo)
                if pm is None:
                    pm = PromocionModel(id=id_promo, id_comercio=id_com, creada_en=ahora)
                    s.add(pm)
                pm.titulo = promo["titulo"]
                pm.descripcion = promo.get("descripcion", "")
                pm.mecanica = promo["mecanica"]
                pm.segmento = promo["segmento"]
                pm.valor_platino = promo.get("valor_platino")
                pm.valor_black = int(promo["valor_black"])
                pm.fecha_desde = _VIGENCIA_DESDE
                pm.fecha_hasta = _VIGENCIA_HASTA
                pm.dias_semana = []
                pm.acumulable = False
                pm.destacada_municipal = False
                pm.monto_minimo = 0
                pm.imagen_url = ""
                pm.estado = "ACTIVA"

                link_pk = {"id_promocion": id_promo, "id_sucursal": id_suc}
                if await s.get(PromocionSucursalModel, link_pk) is None:
                    s.add(PromocionSucursalModel(id_promocion=id_promo, id_sucursal=id_suc))

        await s.commit()
    return len(datos)


def main() -> None:
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else _RUTA_DEFECTO
    datos = yaml.safe_load(ruta.read_text())["comercios"]
    n = asyncio.run(_cargar(datos))
    print(f"Comercios de precarga cargados/actualizados: {n} (desde {ruta})")


if __name__ == "__main__":
    main()
