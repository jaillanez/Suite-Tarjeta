"""Miembro de un grupo (incluye al titular como una fila con rol TITULAR)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from tarjeta.shared.domain.types import EntityId

from .tipos import EstadoMiembro, RolGrupo


@dataclass(slots=True)
class Miembro:
    id: EntityId
    id_grupo: EntityId
    id_persona: str
    rol: RolGrupo
    estado: EstadoMiembro
    fecha_alta: datetime
    tope_mensual: int | None = None  # tope de puntos por mes, opcional (§10.6)

    @classmethod
    def crear(
        cls, *, id_grupo: EntityId, id_persona: str, rol: RolGrupo = RolGrupo.MIEMBRO
    ) -> Miembro:
        return cls(
            id=EntityId.new(),
            id_grupo=id_grupo,
            id_persona=id_persona,
            rol=rol,
            estado=EstadoMiembro.ACTIVO,
            fecha_alta=datetime.now(UTC),
        )

    @property
    def activo(self) -> bool:
        return self.estado is EstadoMiembro.ACTIVO

    def suspender(self) -> None:
        if self.estado is EstadoMiembro.ACTIVO:
            self.estado = EstadoMiembro.SUSPENDIDO

    def reactivar(self) -> None:
        if self.estado is EstadoMiembro.SUSPENDIDO:
            self.estado = EstadoMiembro.ACTIVO

    def dar_de_baja(self) -> None:
        self.estado = EstadoMiembro.BAJA
