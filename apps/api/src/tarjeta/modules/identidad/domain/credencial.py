"""Credencial (contraseña hasheada) de una persona."""

from __future__ import annotations

from tarjeta.shared.domain.entity import Entity
from tarjeta.shared.domain.types import EntityId


class Credencial(Entity):
    def __init__(self, *, id: EntityId, id_persona: EntityId, hash: str) -> None:
        super().__init__(id)
        self.id_persona = id_persona
        self.hash = hash

    def actualizar_hash(self, nuevo_hash: str) -> None:
        self.hash = nuevo_hash

    @classmethod
    def crear(cls, *, id_persona: EntityId, hash: str) -> Credencial:
        return cls(id=EntityId.new(), id_persona=id_persona, hash=hash)
