"""Modelos del módulo comercios."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class ComercioModel(Base):
    __tablename__ = "comercio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    cuit: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_fantasia: Mapped[str] = mapped_column(String(200), default="")
    rubro: Mapped[str] = mapped_column(String(80), default="")
    logo_url: Mapped[str] = mapped_column(String(400), default="")
    id_responsable: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    estado: Mapped[str] = mapped_column(String(30), index=True)
    convenio_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    convenio_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    convenio_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SucursalModel(Base):
    __tablename__ = "sucursal"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_comercio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    lat: Mapped[float] = mapped_column()
    lon: Mapped[float] = mapped_column()
    # Índice espacial (GiST) para la consulta de cercanía (§06.3). Se deriva de lat/lon.
    ubicacion: Mapped[Any] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    estado: Mapped[str] = mapped_column(String(30), index=True)
    es_casa_central: Mapped[bool] = mapped_column(Boolean, default=False)
    horarios: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    fotos: Mapped[list[str]] = mapped_column(JSONB, default=list)
    qr_token: Mapped[str] = mapped_column(Text, default="")
    motivo_cierre: Mapped[str] = mapped_column(Text, default="")
    reapertura_estimada: Mapped[str | None] = mapped_column(String(40), nullable=True)


class UsuarioComercioModel(Base):
    __tablename__ = "usuario_comercio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_comercio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    rol: Mapped[str] = mapped_column(String(30))
    sucursales: Mapped[list[str]] = mapped_column(JSONB, default=list)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    pin_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    huella_dispositivo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pin_intentos: Mapped[int] = mapped_column(Integer, default=0)
    pin_bloqueado_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class InvitacionComercioModel(Base):
    __tablename__ = "invitacion_comercio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_comercio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    rol: Mapped[str] = mapped_column(String(30))
    sucursales: Mapped[list[str]] = mapped_column(JSONB, default=list)
    destino: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TurnoModel(Base):
    __tablename__ = "turno_comercio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_sucursal: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    id_cajero: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    abierto_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumen: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
