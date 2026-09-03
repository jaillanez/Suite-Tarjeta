"""Puertos del módulo ciudadania."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .excepcion import ExcepcionNivel
from .historial_nivel import HistorialNivel
from .perfil_ciudadano import PerfilCiudadano


class PerfilCiudadanoRepository(Protocol):
    async def obtener(self, id_persona: EntityId) -> PerfilCiudadano | None: ...
    async def agregar(self, perfil: PerfilCiudadano) -> None: ...
    async def guardar(self, perfil: PerfilCiudadano) -> None: ...


class HistorialNivelRepository(Protocol):
    async def agregar(self, historial: HistorialNivel) -> None: ...


class ExcepcionRepository(Protocol):
    async def agregar(self, excepcion: ExcepcionNivel) -> None: ...
    async def hay_black_vigente(self, id_persona: EntityId, ahora: datetime) -> bool: ...
    async def listar(self, id_persona: EntityId) -> list[ExcepcionNivel]: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...


class RateLimiter(Protocol):
    async def permitido(self, clave: str, limite: int, ventana_seg: int) -> bool: ...
