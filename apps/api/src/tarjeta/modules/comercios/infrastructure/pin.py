"""Hash del PIN de cajero (§06.5). Argon2id, como las contraseñas."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Argon2PinHasher:
    def __init__(self) -> None:
        self._ph = PasswordHasher()

    def hash(self, pin: str) -> str:
        return self._ph.hash(pin)

    def verificar(self, hash: str, pin: str) -> bool:
        try:
            return self._ph.verify(hash, pin)
        except VerifyMismatchError:
            return False
