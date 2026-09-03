"""Eventos de dominio de identidad (se publican por el outbox)."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonaRegistrada(DomainEvent):
    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CelularVerificado(DomainEvent):
    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentidadVerificada(DomainEvent):
    id_persona: str
    dni: str
    metodo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentidadRechazada(DomainEvent):
    id_persona: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonaSuspendida(DomainEvent):
    id_persona: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SesionIniciada(DomainEvent):
    id_persona: str
    perfil: str


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentoDeLoginFallido(DomainEvent):
    # No incluye datos personales: solo un hash de búsqueda o "desconocido".
    identificador_hash: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PerfilCambiado(DomainEvent):
    id_persona: str
    perfil: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DispositivoRevocado(DomainEvent):
    id_persona: str
    id_dispositivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsentimientoOtorgado(DomainEvent):
    id_persona: str
    tipo: str
    version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsentimientoRevocado(DomainEvent):
    id_persona: str
    tipo: str
