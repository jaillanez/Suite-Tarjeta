"""Unit: guardas de arranque en producción (§12.2-D) y ausencia de RENAPER (§12.2-C)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from tarjeta.config import Settings
from tarjeta.shared.infrastructure.arranque import ArranqueInseguro, validar_arranque

# Clave de cifrado válida (32 bytes base64 urlsafe) para aislar el caso bajo prueba.
_CLAVE_OK = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
_JWT_OK = "un-secreto-de-produccion-larguisimo-y-serio-1234"


def _settings(**over: object) -> Settings:
    base: dict[str, object] = {
        "environment": "prod",
        "database_url": "postgresql+psycopg://u@localhost/db",
        "database_migrator_url": "postgresql+psycopg://m@localhost/db",
        "redis_url": "redis://localhost:6379/0",
        "padron_base_url": "https://padron.rivadavia.gob.ar",
        "padron_api_key": SecretStr("k"),
        "padron_modo": "real",
        "contenido_proveedor": "real",
        "jwt_secret": SecretStr(_JWT_OK),
        "field_pepper": SecretStr("pepper"),
        "field_encryption_key": SecretStr(_CLAVE_OK),
        "cors_origins": ["https://app.rivadavia.gob.ar"],
    }
    base.update(over)
    return Settings(**base)  # type: ignore[arg-type]


def test_prod_todo_real_arranca() -> None:
    validar_arranque(_settings())  # no lanza


def test_dev_no_valida_nada() -> None:
    validar_arranque(_settings(environment="dev", padron_modo="simulacion"))  # dev: permitido


def test_prod_bloquea_padron_simulado() -> None:
    with pytest.raises(ArranqueInseguro, match="padrón"):
        validar_arranque(_settings(padron_modo="simulacion"))


def test_prod_bloquea_imagenes_simuladas() -> None:
    with pytest.raises(ArranqueInseguro, match="imágenes"):
        validar_arranque(_settings(contenido_proveedor="simulacion"))


def test_prod_bloquea_jwt_debil() -> None:
    with pytest.raises(ArranqueInseguro, match="JWT"):
        validar_arranque(_settings(jwt_secret=SecretStr("dev-insecure-secret")))


def test_prod_bloquea_clave_cifrado_invalida() -> None:
    with pytest.raises(ArranqueInseguro, match="cifrado"):
        validar_arranque(_settings(field_encryption_key=SecretStr("no-es-base64-de-32-bytes")))


def test_prod_bloquea_cors_permisivo() -> None:
    with pytest.raises(ArranqueInseguro, match="CORS"):
        validar_arranque(_settings(cors_origins=["*"]))


def test_renaper_no_es_metodo_de_verificacion() -> None:
    from tarjeta.modules.identidad.domain.persona import MetodoVerificacion

    assert not hasattr(MetodoVerificacion, "RENAPER")
    assert "RENAPER" not in {m.value for m in MetodoVerificacion}
    assert MetodoVerificacion.AUTODECLARADA.value == "AUTODECLARADA"


def test_renaper_fuera_del_codigo_activo() -> None:
    # §12.2-C: RENAPER no puede quedar como token de código (comentarios que explican su baja y la
    # migración que reetiqueta los registros viejos están permitidos).
    src = Path(__file__).resolve().parents[2] / "src" / "tarjeta"
    ofensores: list[str] = []
    for p in src.rglob("*.py"):
        if "/migrations/" in p.as_posix():
            continue
        for n, linea in enumerate(p.read_text().splitlines(), 1):
            codigo = linea.split("#", 1)[0]  # ignora comentarios
            if "RENAPER" in codigo or "renaper" in codigo:
                ofensores.append(f"{p.name}:{n}")
    assert ofensores == [], f"RENAPER sigue en código activo: {ofensores}"
