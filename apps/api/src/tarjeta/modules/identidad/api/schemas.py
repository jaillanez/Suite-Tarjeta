"""Schemas Pydantic de la API de identidad."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConsentimientoIn(BaseModel):
    tipo: str
    otorgado: bool


class RegistroRequest(BaseModel):
    dni: str
    cuil: str
    apellido: str = Field(min_length=1, max_length=120)
    nombre: str = Field(min_length=1, max_length=120)
    celular: str
    password: str = Field(min_length=1)
    email: str | None = None
    consentimientos: list[ConsentimientoIn] = Field(default_factory=list)


class VerificarCelularRequest(BaseModel):
    celular: str
    codigo: str


class ReenviarOtpRequest(BaseModel):
    celular: str


class LoginRequest(BaseModel):
    dni: str
    password: str


class MfaVerificarRequest(BaseModel):
    mfa_token: str
    codigo: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RecuperarRequest(BaseModel):
    dni: str


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PerfilOut(BaseModel):
    clave: str
    tipo: str
    id_comercio: str | None = None
    rol: str | None = None


class LoginResponse(BaseModel):
    mfa_requerido: bool
    perfiles: list[PerfilOut]
    perfil_activo: str | None = None
    tokens: TokensResponse | None = None
    mfa_token: str | None = None


class PersonaMeResponse(BaseModel):
    id: str
    dni: str
    cuil: str
    apellido: str
    nombre: str
    celular: str
    email: str | None
    estado_identidad: str
    celular_verificado: bool
    perfiles: list[PerfilOut]


class PersonaPatchRequest(BaseModel):
    email: str | None = None


class DispositivoCrearRequest(BaseModel):
    nombre_declarado: str
    plataforma: str
    huella: str


class DispositivoResponse(BaseModel):
    id: str
    nombre_declarado: str
    plataforma: str
    estado: str
    autorizado_para_perfil_municipal: bool


class MfaActivarResponse(BaseModel):
    secreto: str
    uri: str
    codigos_recuperacion: list[str]


class MensajeResponse(BaseModel):
    mensaje: str
