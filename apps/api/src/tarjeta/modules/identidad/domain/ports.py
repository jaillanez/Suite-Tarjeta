"""Puertos (interfaces) del módulo identidad. Las implementaciones viven en infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .consentimiento import Consentimiento, TipoConsentimiento
from .credencial import Credencial
from .dispositivo import Dispositivo
from .persona import Persona


# --- seguridad ---------------------------------------------------------------
class HashDeContrasena(Protocol):
    def hash(self, password: str) -> str: ...
    def verificar(self, hash: str, password: str) -> bool: ...
    def necesita_rehash(self, hash: str) -> bool: ...


class GeneradorTotp(Protocol):
    def generar_secreto(self) -> str: ...
    def uri(self, secreto: str, cuenta: str) -> str: ...
    def verificar(self, secreto: str, codigo: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class Claims:
    id_persona: str
    perfil: str
    permisos: list[str]
    huella: str | None = None


class GeneradorTokenAcceso(Protocol):
    def crear(
        self, *, id_persona: str, perfil: str, permisos: list[str], huella: str | None = None
    ) -> str: ...
    def decodificar(self, token: str) -> Claims: ...


@dataclass(frozen=True, slots=True)
class Rotacion:
    id_persona: EntityId
    perfil: str
    nuevo_token: str


class AlmacenRefresh(Protocol):
    async def emitir(self, id_persona: EntityId, perfil: str) -> str: ...
    async def rotar(self, token_plano: str) -> Rotacion: ...
    async def revocar(self, token_plano: str) -> None: ...
    async def revocar_todo_de(self, id_persona: EntityId) -> None: ...


# --- OTP / verificación de contacto ------------------------------------------
class EnvioOtp(Protocol):
    async def enviar(self, celular: str, codigo: str) -> None: ...


class AlmacenOtp(Protocol):
    async def emitir(self, clave: str, codigo: str, ttl_seg: int) -> None: ...
    async def verificar_y_consumir(self, clave: str, codigo: str, max_intentos: int) -> bool: ...


class RateLimiter(Protocol):
    async def permitido(self, clave: str, limite: int, ventana_seg: int) -> bool: ...


# --- recuperación de cuenta por email ----------------------------------------
class EnviarEmail(Protocol):
    async def enviar(self, email: str, asunto: str, cuerpo: str) -> None: ...


class AlmacenReset(Protocol):
    """Token de recuperación de un solo uso: token -> id_persona, con TTL."""

    async def emitir(self, token: str, id_persona: str, ttl_seg: int) -> None: ...
    async def consumir(self, token: str) -> str | None: ...


# --- repositorios ------------------------------------------------------------
class PersonaRepository(Protocol):
    async def agregar(self, persona: Persona) -> None: ...
    async def guardar(self, persona: Persona) -> None: ...
    async def obtener_por_id(self, id: EntityId) -> Persona | None: ...
    async def obtener_por_dni(self, dni: str) -> Persona | None: ...
    async def obtener_por_celular(self, celular: str) -> Persona | None: ...
    async def obtener_por_email(self, email: str) -> Persona | None: ...
    async def existe_dni(self, dni: str) -> bool: ...
    async def existe_cuil(self, cuil: str) -> bool: ...


class CredencialRepository(Protocol):
    async def agregar(self, credencial: Credencial) -> None: ...
    async def guardar(self, credencial: Credencial) -> None: ...
    async def obtener_por_persona(self, id_persona: EntityId) -> Credencial | None: ...


class DispositivoRepository(Protocol):
    async def agregar(self, dispositivo: Dispositivo) -> None: ...
    async def guardar(self, dispositivo: Dispositivo) -> None: ...
    async def obtener(self, id: EntityId) -> Dispositivo | None: ...
    async def listar_por_persona(self, id_persona: EntityId) -> list[Dispositivo]: ...


class ConsentimientoRepository(Protocol):
    async def agregar(self, consentimiento: Consentimiento) -> None: ...
    async def listar_por_persona(self, id_persona: EntityId) -> list[Consentimiento]: ...
    async def ultimo_por_tipo(
        self, id_persona: EntityId, tipo: TipoConsentimiento
    ) -> Consentimiento | None: ...


@dataclass(frozen=True, slots=True)
class MfaEstado:
    secreto: str
    activo: bool
    codigos_recuperacion: list[str]


class AlmacenMfa(Protocol):
    async def obtener(self, id_persona: EntityId) -> MfaEstado | None: ...
    async def guardar(
        self,
        id_persona: EntityId,
        *,
        secreto: str,
        activo: bool,
        codigos_recuperacion: list[str],
    ) -> None: ...


class TextosLegales(Protocol):
    async def version_vigente(self, tipo: TipoConsentimiento) -> str | None: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...
