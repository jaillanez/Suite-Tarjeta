"""Agregado Comercio (§4.1) con la máquina de estados de adhesión (§06.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import ConvenioNoAceptado, TransicionComercioInvalida
from .events import ComercioAdherido, EstadoComercioCambiado


class EstadoComercio(StrEnum):
    SOLICITADA = "SOLICITADA"
    EN_REVISION = "EN_REVISION"
    DOCUMENTACION_PENDIENTE = "DOCUMENTACION_PENDIENTE"
    APROBADA = "APROBADA"
    ACTIVA = "ACTIVA"
    SUSPENDIDA = "SUSPENDIDA"
    RECHAZADA = "RECHAZADA"
    BAJA = "BAJA"


# Transiciones válidas (§06.2). Cada arista lleva motivo y auditoría en la capa de aplicación.
_TRANSICIONES: dict[EstadoComercio, set[EstadoComercio]] = {
    EstadoComercio.SOLICITADA: {EstadoComercio.EN_REVISION, EstadoComercio.RECHAZADA},
    EstadoComercio.EN_REVISION: {
        EstadoComercio.APROBADA,
        EstadoComercio.DOCUMENTACION_PENDIENTE,
        EstadoComercio.RECHAZADA,
    },
    EstadoComercio.DOCUMENTACION_PENDIENTE: {EstadoComercio.EN_REVISION, EstadoComercio.RECHAZADA},
    EstadoComercio.APROBADA: {EstadoComercio.ACTIVA},
    EstadoComercio.ACTIVA: {EstadoComercio.SUSPENDIDA, EstadoComercio.BAJA},
    EstadoComercio.SUSPENDIDA: {EstadoComercio.ACTIVA, EstadoComercio.BAJA},
    EstadoComercio.RECHAZADA: set(),
    EstadoComercio.BAJA: set(),
}


@dataclass(frozen=True, slots=True)
class EvidenciaConvenio:
    """Evidencia de aceptación del convenio de adhesión (§06.2, versionado)."""

    version: str
    fecha: datetime
    ip: str


class Comercio(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        cuit: str,
        razon_social: str,
        nombre_fantasia: str,
        rubro: str,
        logo_url: str,
        id_responsable: EntityId,
        estado: EstadoComercio,
        convenio: EvidenciaConvenio | None,
        creado_en: datetime,
    ) -> None:
        super().__init__(id)
        self.cuit = cuit
        self.razon_social = razon_social
        self.nombre_fantasia = nombre_fantasia
        self.rubro = rubro
        self.logo_url = logo_url
        self.id_responsable = id_responsable
        self._estado = estado
        self.convenio = convenio
        self.creado_en = creado_en

    @classmethod
    def solicitar(
        cls,
        *,
        cuit: str,
        razon_social: str,
        nombre_fantasia: str,
        rubro: str,
        logo_url: str,
        id_responsable: EntityId,
        convenio: EvidenciaConvenio | None,
    ) -> Comercio:
        # El convenio es el único instrumento que obliga al comercio (§06.2): sin él, no hay alta.
        if convenio is None:
            raise ConvenioNoAceptado("Hay que aceptar el convenio de adhesión para solicitar.")
        comercio = cls(
            id=EntityId.new(),
            cuit=cuit,
            razon_social=razon_social,
            nombre_fantasia=nombre_fantasia,
            rubro=rubro,
            logo_url=logo_url,
            id_responsable=id_responsable,
            estado=EstadoComercio.SOLICITADA,
            convenio=convenio,
            creado_en=datetime.now(UTC),
        )
        comercio.record_event(ComercioAdherido(id_comercio=str(comercio.id), cuit=cuit))
        return comercio

    @property
    def estado(self) -> EstadoComercio:
        return self._estado

    def transicionar(self, destino: EstadoComercio, *, motivo: str = "") -> None:
        if destino not in _TRANSICIONES[self._estado]:
            raise TransicionComercioInvalida(
                f"No se puede pasar de {self._estado.value} a {destino.value}."
            )
        anterior = self._estado
        self._estado = destino
        self.record_event(
            EstadoComercioCambiado(
                id_comercio=str(self.id),
                estado_anterior=anterior.value,
                estado_nuevo=destino.value,
                motivo=motivo,
            )
        )
