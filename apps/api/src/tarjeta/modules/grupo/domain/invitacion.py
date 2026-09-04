"""Invitación al grupo (§10.3): declaración del titular + aceptación explícita del invitado.

Sin canal de notificaciones, la invitación se entrega por código/enlace que el titular comparte a
mano, con vencimiento de 7 días. El titular acepta un texto de responsabilidad al invitar (queda
la evidencia: fecha e IP); el invitado acepta explícitamente antes de entrar.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tarjeta.shared.domain.types import EntityId

from .errors import InvitacionInvalida, InvitacionVencida
from .tipos import EstadoInvitacion

TEXTO_DECLARACION = (
    "Declarás que esta persona integra tu grupo familiar. Sos responsable de lo que declarás."
)
VENCIMIENTO_DIAS = 7


@dataclass(slots=True)
class Invitacion:
    id: EntityId
    id_grupo: EntityId
    token: str
    texto_declaracion: str
    id_titular: str
    ip_titular: str
    declarada_en: datetime
    vence_en: datetime
    estado: EstadoInvitacion
    aceptada_por: str | None = None
    aceptada_en: datetime | None = None

    @classmethod
    def crear(
        cls, *, id_grupo: EntityId, id_titular: str, ip_titular: str, dias: int = VENCIMIENTO_DIAS
    ) -> Invitacion:
        ahora = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            id_grupo=id_grupo,
            token=secrets.token_urlsafe(16),
            texto_declaracion=TEXTO_DECLARACION,
            id_titular=id_titular,
            ip_titular=ip_titular,
            declarada_en=ahora,
            vence_en=ahora + timedelta(days=dias),
            estado=EstadoInvitacion.PENDIENTE,
        )

    def vigente(self, ahora: datetime) -> bool:
        return self.estado is EstadoInvitacion.PENDIENTE and ahora <= self.vence_en

    def aceptar(self, *, id_invitado: str, ahora: datetime) -> None:
        if self.estado is not EstadoInvitacion.PENDIENTE:
            raise InvitacionInvalida("La invitación ya no está disponible.")
        if ahora > self.vence_en:
            self.estado = EstadoInvitacion.VENCIDA
            raise InvitacionVencida("La invitación venció.")
        self.estado = EstadoInvitacion.ACEPTADA
        self.aceptada_por = id_invitado
        self.aceptada_en = ahora
