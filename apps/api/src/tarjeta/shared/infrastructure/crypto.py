"""Cifrado a nivel de campo (§8.3).

Dos primitivas:
- `search_hash`: HMAC-SHA256 con *pepper* de aplicación, para indexar y comparar por
  igualdad datos sensibles (DNI, CUIL) sin exponerlos.
- `FieldCipher`: cifrado simétrico AES-256-GCM para recuperar el valor cuando hace falta
  mostrarlo. El texto cifrado lleva prefijo de versión de clave (soporta rotación).

El *pepper* y la clave viven en configuración, nunca en la base de datos.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def normalizar_documento(valor: str) -> str:
    """Deja solo dígitos: el mismo documento con o sin puntos/guiones hashea igual."""
    return "".join(ch for ch in valor if ch.isdigit())


def search_hash(valor: str, pepper: str) -> str:
    """HMAC-SHA256 del valor normalizado con el pepper. Hex de 64 caracteres."""
    normalizado = normalizar_documento(valor)
    return hmac.new(pepper.encode(), normalizado.encode(), hashlib.sha256).hexdigest()


class FieldCipher:
    """AES-256-GCM con versión de clave en el prefijo del texto cifrado."""

    def __init__(self, key_b64: str, version: str) -> None:
        key = base64.urlsafe_b64decode(key_b64)
        if len(key) not in (16, 24, 32):
            raise ValueError("La clave de cifrado debe ser de 16, 24 o 32 bytes (base64).")
        self._aes = AESGCM(key)
        self._version = version

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, plaintext.encode(), None)
        blob = base64.urlsafe_b64encode(nonce + ct).decode()
        return f"{self._version}:{blob}"

    def decrypt(self, token: str) -> str:
        _version, blob = token.split(":", 1)
        raw = base64.urlsafe_b64decode(blob)
        nonce, ct = raw[:12], raw[12:]
        return self._aes.decrypt(nonce, ct, None).decode()
