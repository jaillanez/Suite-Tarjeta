"""Eventos de dominio del grupo familiar."""

from __future__ import annotations

from dataclasses import dataclass, field

from tarjeta.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class GrupoCreado(DomainEvent):
    id_grupo: str
    id_titular: str
    modo_billetera: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MiembroInvitado(DomainEvent):
    id_grupo: str
    id_titular: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MiembroAgregado(DomainEvent):
    id_grupo: str
    id_titular: str
    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MiembroSalio(DomainEvent):
    id_grupo: str
    id_persona: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ModoBilleteraCambiado(DomainEvent):
    id_grupo: str
    modo_anterior: str
    modo_nuevo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TitularSucedido(DomainEvent):
    id_grupo: str
    id_titular_anterior: str
    id_titular_nuevo: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GrupoDisuelto(DomainEvent):
    id_grupo: str
    id_titular: str
    id_miembros: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertaAntifraudeGrupo(DomainEvent):
    """Señal que SOLO observa: genera un caso, nunca bloquea un alta (§10.7)."""

    id_grupo: str
    tipo: str
    detalle: str
