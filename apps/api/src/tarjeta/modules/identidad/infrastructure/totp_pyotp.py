"""Generador/verificador TOTP con pyotp."""

from __future__ import annotations

import pyotp


class TotpPyotp:
    def __init__(self, *, issuer: str) -> None:
        self._issuer = issuer

    def generar_secreto(self) -> str:
        return pyotp.random_base32()

    def uri(self, secreto: str, cuenta: str) -> str:
        return pyotp.TOTP(secreto).provisioning_uri(name=cuenta, issuer_name=self._issuer)

    def verificar(self, secreto: str, codigo: str) -> bool:
        return pyotp.TOTP(secreto).verify(codigo, valid_window=1)
