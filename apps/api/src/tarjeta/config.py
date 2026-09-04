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

    # Outbox de eventos (§05.1): cada cuánto drena el worker de segundo plano.
    outbox_intervalo_seg: float = 5.0

    # Endpoint del padrón municipal
    padron_base_url: str
    padron_api_key: SecretStr
    padron_timeout_seconds: float = 5.0
    padron_cache_ttl_seconds: int = 21600  # 6 h
    padron_modo: Literal["real", "simulacion"] = "simulacion"
    padron_sim_archivo: str = ""  # JSON con respuestas por DNI/CUIT (opcional)

    # Seguridad
    jwt_secret: SecretStr
    jwt_access_ttl_seconds: int = 900
    qr_token_rotation_seconds: int = 45
    qr_token_validity_seconds: int = 90

    # Cifrado a nivel de campo (§8.3)
    # pepper: clave secreta del HMAC de búsqueda (dni_hash, cuil_hash). Nunca en la base.
    field_pepper: SecretStr
    # clave de cifrado simétrico (base64 urlsafe de 32 bytes) y su versión (rotación).
    field_encryption_key: SecretStr
    field_encryption_key_version: str = "v1"

    # Contraseñas (argon2id)
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # 64 MiB
    argon2_parallelism: int = 4
    password_min_length: int = 10

    # Sesiones
    refresh_ttl_seconds: int = 1209600  # 14 días
    sesion_ciudadano_timeout_minutos: int = 43200  # 30 días (generoso)
    sesion_comercio_timeout_minutos: int = 30

    # Cajero (§06.5): PIN atado a dispositivo, con límite de intentos y bloqueo temporal.
    cajero_pin_max_intentos: int = 5
    cajero_pin_bloqueo_seg: int = 300
    sesion_cajero_timeout_minutos: int = 30

    # Canje (§08): confirmación del ciudadano, comprobante y límites del modo sin conexión.
    canje_confirmacion_ttl_seg: int = 90
    comprobante_prefijo: str = "RIV"
    canje_offline_monto_max: int = 50000
    canje_offline_max_operaciones: int = 50

    # OTP
    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_intentos: int = 5
    otp_max_solicitudes_por_hora: int = 5

    # MFA
    mfa_issuer: str = "Tarjeta de Beneficios"

    # Contenido / generación de piezas (§11.2). El proveedor NO se elige acá: simulación por
    # defecto; el real exige API key. Las variantes por crédito son la palanca de costo.
    contenido_proveedor: Literal["simulacion", "real"] = "simulacion"
    contenido_ia_modelo: str = "simulacion"
    contenido_ia_tamano: str = "1024x1024"
    contenido_variantes_por_credito: int = 4
    contenido_ia_api_key: SecretStr = SecretStr("")
    contenido_ia_base_url: str = ""
    contenido_ia_precio_unitario_centavos: int = 0  # para el cálculo de costo mensual
    contenido_almacen_dir: str = "var/contenido"  # almacén de objetos local (dev)

    # Rate limiting (login/registro/recuperación)
    rate_limit_login_por_minuto: int = 10
    rate_limit_registro_por_hora: int = 5  # reforzado: única contención sin OTP (§04.0.B)

    # Parámetros del programa (§13 de la especificación)
    puntos_vencimiento_meses: int = 24
    # Puntos (PASO 09/10): los PC salen SOLO del reparto de la promoción (§10.0.A), por eso la
    # acreditación automática base arranca en cero.
    puntos_base_por_cien: int = 0  # acreditación automática por cada 100 pesos (0 = desactivada)
    puntos_valor_peso: int = 1  # pesos que vale un punto al pagar con puntos
    pm_al_dia: int = 50  # PM por estar al día (regla, §09.5)
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
    # §10.0.B: la generación de PM queda apagada hasta que el municipio cargue inventario real
    # (juntar puntos contra un catálogo vacío frustra más que no tenerlos).
    ff_generacion_pm: bool = False
    ff_generacion_ia: bool = True
    ff_publicacion_redes: bool = True
    # §12.2-C: se conserva APAGADA y sin afectar canjes. Registro abierto + identidad AUTODECLARADA
    # (§3.1 v2.3): canjear no exige identidad verificada. El día que exista verificación reforzada
    # (PRESENCIAL/DOCUMENTAL) para ciertas operaciones futuras, se podrá prender.
    ff_exigir_identidad_verificada: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TARJETA_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (una sola lectura del entorno)."""
    return Settings()  # type: ignore[call-arg]
