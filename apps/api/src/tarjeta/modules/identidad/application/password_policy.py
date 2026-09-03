"""Política mínima de contraseñas (§03.3): longitud y lista de comunes.

Sin complejidad artificial (mayúscula/número/símbolo): empeora las contraseñas reales.
"""

from __future__ import annotations

from tarjeta.shared.domain.errors import ValidationError

# Muestra corta de contraseñas comunes. En producción se usa una lista más amplia.
_COMUNES: frozenset[str] = frozenset(
    {
        "12345678",
        "123456789",
        "1234567890",
        "password",
        "contrasena",
        "contraseña",
        "qwertyuiop",
        "11111111",
        "00000000",
        "iloveyou",
        "admin1234",
    }
)


def validar_password(password: str, *, min_length: int) -> None:
    if len(password) < min_length:
        raise ValidationError(f"La contraseña debe tener al menos {min_length} caracteres.")
    if password.lower() in _COMUNES:
        raise ValidationError("Esa contraseña es demasiado común. Elegí otra.")
