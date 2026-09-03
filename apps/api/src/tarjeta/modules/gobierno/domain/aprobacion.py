"""Doble conformidad: SolicitudAprobacion (§05.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from tarjeta.shared.domain.types import EntityId

from .errors import AutoaprobacionProhibida, RangoInsuficiente, SolicitudNoAprobable
from .roles import RolMunicipal, rango_suficiente

_EXPIRACION_HORAS = 72


class EstadoSolicitud(StrEnum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    EXPIRADA = "EXPIRADA"
    ERROR = "ERROR"


@dataclass(slots=True)
class SolicitudAprobacion:
    id: EntityId
    accion: str
    payload: dict[str, Any]
    id_solicitante: str
    rol_solicitante: RolMunicipal
    estado: EstadoSolicitud
    fecha_solicitud: datetime
    fecha_expiracion: datetime
    id_aprobador: str | None = None
    motivo_decision: str | None = None
    fecha_decision: datetime | None = None

    @classmethod
    def crear(
        cls, *, accion: str, payload: dict[str, Any], id_solicitante: str, rol: RolMunicipal
    ) -> SolicitudAprobacion:
        ahora = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            accion=accion,
            payload=payload,
            id_solicitante=id_solicitante,
            rol_solicitante=rol,
            estado=EstadoSolicitud.PENDIENTE,
            fecha_solicitud=ahora,
            fecha_expiracion=ahora + timedelta(hours=_EXPIRACION_HORAS),
        )

    def esta_vigente(self, ahora: datetime) -> bool:
        return self.estado is EstadoSolicitud.PENDIENTE and ahora <= self.fecha_expiracion

    def aprobar(self, *, id_aprobador: str, rol_aprobador: RolMunicipal, motivo: str) -> None:
        ahora = datetime.now(UTC)
        if not self.esta_vigente(ahora):
            raise SolicitudNoAprobable("La solicitud no está pendiente o expiró.")
        if id_aprobador == self.id_solicitante:
            raise AutoaprobacionProhibida("No podés aprobar tu propia solicitud.")
        if not rango_suficiente(rol_aprobador, self.rol_solicitante):
            raise RangoInsuficiente("Se requiere un rol igual o superior al solicitante.")
        self.estado = EstadoSolicitud.APROBADA
        self.id_aprobador = id_aprobador
        self.motivo_decision = motivo
        self.fecha_decision = ahora

    def rechazar(self, *, id_aprobador: str, motivo: str) -> None:
        if not self.esta_vigente(datetime.now(UTC)):
            raise SolicitudNoAprobable("La solicitud no está pendiente o expiró.")
        if id_aprobador == self.id_solicitante:
            raise AutoaprobacionProhibida("No podés decidir sobre tu propia solicitud.")
        self.estado = EstadoSolicitud.RECHAZADA
        self.id_aprobador = id_aprobador
        self.motivo_decision = motivo
        self.fecha_decision = datetime.now(UTC)

    def marcar_error(self, detalle: str) -> None:
        self.estado = EstadoSolicitud.ERROR
        self.motivo_decision = detalle
