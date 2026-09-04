"""Modelos del módulo grupo."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class GrupoModel(Base):
    __tablename__ = "grupo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_titular: Mapped[str] = mapped_column(String(64), index=True)
    modo_billetera: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MiembroModel(Base):
    __tablename__ = "miembro_grupo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_grupo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    id_persona: Mapped[str] = mapped_column(String(64), index=True)
    rol: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    fecha_alta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tope_mensual: Mapped[int | None] = mapped_column(Integer, nullable=True)


class InvitacionModel(Base):
    __tablename__ = "invitacion_grupo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_grupo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    texto_declaracion: Mapped[str] = mapped_column(Text)
    id_titular: Mapped[str] = mapped_column(String(64))
    ip_titular: Mapped[str] = mapped_column(String(64))
    declarada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    aceptada_por: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aceptada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertaGrupoModel(Base):
    __tablename__ = "alerta_grupo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_grupo: Mapped[str] = mapped_column(String(64), index=True)
    tipo: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
