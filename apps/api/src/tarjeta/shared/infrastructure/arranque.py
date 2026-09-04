"""Guardas de arranque en producción (§12.2-D).

Se acumularon simulaciones (padrón, OTP por consola, recuperación por email, generación de
imágenes). La aplicación debe **negarse a iniciar** en `environment = prod` si detecta cualquier
simulación crítica activa o una configuración insegura. Bloquear el arranque es preferible a un
despliegue inseguro silencioso.
"""

from __future__ import annotations

import base64

from tarjeta.config import Settings

# Marcadores de secretos de desarrollo que jamás deben llegar a producción.
_DEBILES = ("insecure", "change", "dev", "dummy", "test", "example", "cambiar")


class ArranqueInseguro(RuntimeError):
    """La configuración no es apta para producción; el arranque se aborta."""


def _clave_cifrado_valida(valor: str) -> bool:
    # binascii.Error hereda de ValueError; se evita el except-tupla que ruff format corrompe.
    try:
        return len(base64.urlsafe_b64decode(valor)) == 32
    except ValueError:
        return False


def validar_arranque(settings: Settings) -> None:
    """Aborta el arranque en `prod` con cualquier simulación crítica o config insegura."""
    if settings.environment != "prod":
        return

    problemas: list[str] = []

    # Integraciones críticas en simulación (el padrón simulado, además, usa paridad de DNI/CUIT,
    # que en prod habilitaría comercios por tener un CUIT par).
    if settings.padron_modo != "real":
        problemas.append("padrón en modo simulación (TARJETA_PADRON_MODO != real)")
    if settings.contenido_proveedor != "real":
        problemas.append("generación de imágenes en simulación (CONTENIDO_PROVEEDOR != real)")

    # Secretos y cifrado.
    secreto = settings.jwt_secret.get_secret_value()
    if len(secreto) < 32 or any(w in secreto.lower() for w in _DEBILES):
        problemas.append("secreto JWT débil o de desarrollo")
    if not _clave_cifrado_valida(settings.field_encryption_key.get_secret_value()):
        problemas.append("clave de cifrado inválida (se esperan 32 bytes base64 urlsafe)")

    # CORS permisivo.
    if "*" in settings.cors_origins:
        problemas.append("CORS permisivo (origen '*')")

    if problemas:
        raise ArranqueInseguro(
            "No se puede arrancar en producción con: " + "; ".join(problemas) + ". "
            "Configurá las integraciones reales y los secretos antes de desplegar."
        )
