"""Eventos de dominio del módulo comercios (se publican por el outbox)."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ComercioAdherido(DomainEvent):
    id_comercio: str
    cuit: str


@dataclass(frozen=True, slots=True, kw_only=True)
class EstadoComercioCambiado(DomainEvent):
    id_comercio: str
    estado_anterior: str
    estado_nuevo: str
    motivo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SucursalCreada(DomainEvent):
    id_comercio: str
    id_sucursal: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UsuarioComercioInvitado(DomainEvent):
    id_comercio: str
    rol: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UsuarioComercioAceptado(DomainEvent):
    id_comercio: str
    id_persona: str
    rol: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CajeroDadoDeBaja(DomainEvent):
    id_comercio: str
    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnoAbierto(DomainEvent):
    id_sucursal: str
    id_cajero: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnoCerrado(DomainEvent):
    id_sucursal: str
    id_cajero: str
