"""Invitación a un usuario de comercio (§06.4): link con vencimiento a 72 h."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import InvitacionExpirada
from .roles import RolComercio

_VENCIMIENTO_HORAS = 72


class EstadoInvitacion(StrEnum):
    PENDIENTE = "PENDIENTE"
    ACEPTADA = "ACEPTADA"
    EXPIRADA = "EXPIRADA"


class Invitacion(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_comercio: EntityId,
        rol: RolComercio,
        sucursales: list[EntityId],
        destino: str,
        token_hash: str,
        estado: EstadoInvitacion,
        vence_en: datetime,
    ) -> None:
        super().__init__(id)
        self.id_comercio = id_comercio
        self.rol = rol
        self.sucursales = sucursales
        self.destino = destino
        self.token_hash = token_hash
        self.estado = estado
        self.vence_en = vence_en

    @classmethod
    def crear(
        cls,
        *,
        id_comercio: EntityId,
        rol: RolComercio,
        sucursales: list[EntityId],
        destino: str,
        token_hash: str,
    ) -> Invitacion:
        ahora = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            id_comercio=id_comercio,
            rol=rol,
            sucursales=sucursales,
            destino=destino,
            token_hash=token_hash,
            estado=EstadoInvitacion.PENDIENTE,
            vence_en=ahora + timedelta(hours=_VENCIMIENTO_HORAS),
        )

    def aceptar(self, ahora: datetime) -> None:
        if self.estado is not EstadoInvitacion.PENDIENTE or ahora > self.vence_en:
            self.estado = EstadoInvitacion.EXPIRADA
            raise InvitacionExpirada("La invitación venció o ya fue usada.")
        self.estado = EstadoInvitacion.ACEPTADA
