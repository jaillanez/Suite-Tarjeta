"""Configuración de la aplicación.

Toda parametrización vive acá o en variables de entorno; nada de valores fijos
esparcidos por el código. Los datos del municipio (nombre, provincia, zona horaria,
logo) también son configuración: no se escriben literalmente en ningún otro módulo.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Aplicación
    app_name: str = "Tarjeta de Beneficios"
    environment: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False

    # Municipio (configurable, no escrito en el código)
    municipio_nombre: str = "Rivadavia"
    municipio_provincia: str = "San Juan"
    municipio_timezone: str = "America/Argentina/San_Juan"
    municipio_logo_url: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Base de datos
    database_url: PostgresDsn  # rol tarjeta_app — runtime
    database_migrator_url: PostgresDsn  # rol tarjeta_migrator — solo Alembic
    database_pool_size: int = 10

    # Redis
    redis_url: RedisDsn

    # Endpoint del padrón municipal
    padron_base_url: str
    padron_api_key: SecretStr
    padron_timeout_seconds: float = 5.0
    padron_cache_ttl_seconds: int = 21600  # 6 h

    # Seguridad
    jwt_secret: SecretStr
    jwt_access_ttl_seconds: int = 900
    qr_token_rotation_seconds: int = 45
    qr_token_validity_seconds: int = 90

    # Parámetros del programa (§13 de la especificación)
    puntos_vencimiento_meses: int = 24
    grupo_max_miembros: int = 6
    grupo_cooldown_dias: int = 90
    grupo_max_altas_anuales: int = 4
    grupo_max_bajas_anuales: int = 4
    cambio_modo_billetera_dias: int = 180
    anulacion_ventana_minutos: int = 15
    sesion_municipal_timeout_minutos: int = 10
    cuota_ia_mensual_por_comercio: int = 10

    # Feature flags
    ff_canje_contra_tasas: bool = False  # requiere ordenanza, apagado
    ff_generacion_ia: bool = True
    ff_publicacion_redes: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TARJETA_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (una sola lectura del entorno)."""
    return Settings()  # type: ignore[call-arg]
