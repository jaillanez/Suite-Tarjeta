"""Hasher de contraseñas con argon2id."""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import Argon2Error, InvalidHashError


class Argon2Hasher:
    def __init__(self, *, time_cost: int, memory_cost: int, parallelism: int) -> None:
        self._ph = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            type=Type.ID,
        )

    def hash(self, password: str) -> str:
        return self._ph.hash(password)

    def verificar(self, hash: str, password: str) -> bool:
        # Argon2Error es la base de VerifyMismatchError e InvalidHash: evita la tupla en except.
        try:
            return self._ph.verify(hash, password)
        except Argon2Error:
            return False

    def necesita_rehash(self, hash: str) -> bool:
        try:
            return self._ph.check_needs_rehash(hash)
        except InvalidHashError:
            return True
