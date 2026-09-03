"""Consentimientos (§3.1). Inmutables: revocar crea un registro nuevo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from tarjeta.shared.domain.types import EntityId


class TipoConsentimiento(StrEnum):
    TRATAMIENTO_DATOS = "TRATAMIENTO_DATOS"  # obligatorio
    COMUNICACIONES_COMERCIALES = "COMUNICACIONES_COMERCIALES"
    GEOLOCALIZACION = "GEOLOCALIZACION"
    ESTADISTICA_ANONIMA = "ESTADISTICA_ANONIMA"


OBLIGATORIOS: frozenset[TipoConsentimiento] = frozenset({TipoConsentimiento.TRATAMIENTO_DATOS})


@dataclass(frozen=True, slots=True)
class Consentimiento:
    """Registro inmutable de una decisión de consentimiento."""

    id: EntityId
    id_persona: EntityId
    tipo: TipoConsentimiento
    version_texto: str
    otorgado: bool
    fecha: datetime
    ip: str
    user_agent: str

    @classmethod
    def registrar(
        cls,
        *,
        id_persona: EntityId,
        tipo: TipoConsentimiento,
        version_texto: str,
        otorgado: bool,
        ip: str,
        user_agent: str,
    ) -> Consentimiento:
        return cls(
            id=EntityId.new(),
            id_persona=id_persona,
            tipo=tipo,
            version_texto=version_texto,
            otorgado=otorgado,
            fecha=datetime.now(UTC),
            ip=ip,
            user_agent=user_agent,
        )
