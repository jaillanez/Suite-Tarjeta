"""Turno de caja (§06.5): apertura y cierre por cajero, con resumen.

Por ahora el resumen está vacío; se llena cuando exista `canje`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId


class Turno(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_sucursal: EntityId,
        id_cajero: EntityId,
        abierto_en: datetime,
        cerrado_en: datetime | None = None,
        resumen: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(id)
        self.id_sucursal = id_sucursal
        self.id_cajero = id_cajero
        self.abierto_en = abierto_en
        self.cerrado_en = cerrado_en
        self.resumen = resumen or {}

    @classmethod
    def abrir(cls, *, id_sucursal: EntityId, id_cajero: EntityId) -> Turno:
        return cls(
            id=EntityId.new(),
            id_sucursal=id_sucursal,
            id_cajero=id_cajero,
            abierto_en=datetime.now(UTC),
        )

    @property
    def abierto(self) -> bool:
        return self.cerrado_en is None

    def cerrar(self) -> None:
        self.cerrado_en = datetime.now(UTC)
