"""Schemas de entrada/salida del módulo comercios."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Mensaje(BaseModel):
    mensaje: str


class FranjaIn(BaseModel):
    desde: str = Field(examples=["09:00"])
    hasta: str = Field(examples=["13:00"])


class HorarioIn(BaseModel):
    dia: int = Field(ge=0, le=6, description="0=lunes .. 6=domingo")
    franjas: list[FranjaIn] = []


class SucursalIn(BaseModel):
    nombre: str
    direccion: str = ""
    lat: float | None = None
    lon: float | None = None
    telefono: str = ""
    es_casa_central: bool = False
    horarios: list[HorarioIn] = []
    fotos: list[str] = []


class CierreTemporalIn(BaseModel):
    motivo: str
    reapertura_estimada: str | None = None


class SucursalOut(BaseModel):
    id: str
    id_comercio: str
    nombre: str
    direccion: str
    telefono: str
    lat: float
    lon: float
    estado: str
    es_casa_central: bool
    fotos: list[str]
    qr_token: str


class SucursalCercanaOut(BaseModel):
    id: str
    nombre: str
    lat: float
    lon: float
    distancia_m: float


class AbiertoOut(BaseModel):
    abierto: bool


class ComercioOut(BaseModel):
    id: str
    cuit: str
    razon_social: str
    nombre_fantasia: str
    rubro: str
    logo_url: str
    estado: str


class UsuarioComercioOut(BaseModel):
    id: str
    id_persona: str
    rol: str
    sucursales: list[str]
    estado: str


class InvitarIn(BaseModel):
    rol: str
    destino: str
    sucursales: list[str] = []


class InvitacionOut(BaseModel):
    id: str
    token: str


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


class AbrirTurnoIn(BaseModel):
    id_sucursal: str


class TurnoOut(BaseModel):
    id: str


class CierreTurnoOut(BaseModel):
    id: str
    resumen: dict[str, object]
