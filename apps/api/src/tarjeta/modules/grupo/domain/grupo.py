"""Agregado Grupo familiar (§10). El titular declara y es responsable."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .events import GrupoCreado, GrupoDisuelto, ModoBilleteraCambiado, TitularSucedido
from .tipos import EstadoGrupo, ModoBilletera


class Grupo(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_titular: str,
        modo_billetera: ModoBilletera,
        estado: EstadoGrupo,
        creado_en: datetime,
    ) -> None:
        super().__init__(id)
        self.id_titular = id_titular
        self.modo_billetera = modo_billetera
        self.estado = estado
        self.creado_en = creado_en

    @classmethod
    def crear(cls, *, id_titular: str, modo_billetera: ModoBilletera) -> Grupo:
        g = cls(
            id=EntityId.new(),
            id_titular=id_titular,
            modo_billetera=modo_billetera,
            estado=EstadoGrupo.ACTIVO,
            creado_en=datetime.now(UTC),
        )
        g.record_event(
            GrupoCreado(
                id_grupo=str(g.id), id_titular=id_titular, modo_billetera=modo_billetera.value
            )
        )
        return g

    @property
    def activo(self) -> bool:
        return self.estado is EstadoGrupo.ACTIVO

    def cambiar_modo(self, modo: ModoBilletera) -> ModoBilletera:
        """Cambia el modo y devuelve el modo anterior (para que el pozo se traspase si aplica)."""
        anterior = self.modo_billetera
        if modo is not anterior:
            self.modo_billetera = modo
            self.record_event(
                ModoBilleteraCambiado(
                    id_grupo=str(self.id), modo_anterior=anterior.value, modo_nuevo=modo.value
                )
            )
        return anterior

    def suceder_titular(self, id_nuevo_titular: str) -> None:
        anterior = self.id_titular
        self.id_titular = id_nuevo_titular
        self.record_event(
            TitularSucedido(
                id_grupo=str(self.id),
                id_titular_anterior=anterior,
                id_titular_nuevo=id_nuevo_titular,
            )
        )

    def disolver(self, *, id_miembros: list[str]) -> None:
        self.estado = EstadoGrupo.DISUELTO
        self.record_event(
            GrupoDisuelto(
                id_grupo=str(self.id), id_titular=self.id_titular, id_miembros=id_miembros
            )
        )
