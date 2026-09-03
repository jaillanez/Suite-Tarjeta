"""DTOs de entrada/salida del módulo identidad."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ConsentimientoInput:
    tipo: str
    otorgado: bool


@dataclass(frozen=True, slots=True)
class RegistroInput:
    dni: str
    cuil: str
    apellido: str
    nombre: str
    celular: str
    password: str
    consentimientos: list[ConsentimientoInput]
    email: str | None = None
    ip: str = ""
    user_agent: str = ""


@dataclass(frozen=True, slots=True)
class Tokens:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class PerfilInfo:
    clave: str
    tipo: str
    id_comercio: str | None = None
    rol: str | None = None


@dataclass(frozen=True, slots=True)
class LoginResultado:
    mfa_requerido: bool
    perfiles: list[PerfilInfo] = field(default_factory=list)
    perfil_activo: str | None = None
    tokens: Tokens | None = None
    mfa_token: str | None = None


@dataclass(frozen=True, slots=True)
class DispositivoInfo:
    id: str
    nombre_declarado: str
    plataforma: str
    estado: str
    autorizado_para_perfil_municipal: bool


@dataclass(frozen=True, slots=True)
class ActivacionMfa:
    secreto: str
    uri: str
    codigos_recuperacion: list[str]
