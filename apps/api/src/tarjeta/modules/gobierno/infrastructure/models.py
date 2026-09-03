"""Modelos del módulo gobierno."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class RegistroAuditoriaModel(Base):
    __tablename__ = "registro_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    id_persona_actor: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    rol_actor: Mapped[str | None] = mapped_column(String(30), nullable=True)
    perfil_activo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    accion: Mapped[str] = mapped_column(String(80), index=True)
    entidad: Mapped[str] = mapped_column(String(60), index=True)
    id_entidad: Mapped[str] = mapped_column(String(64))
    valor_anterior: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    valor_nuevo: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(400), default="")
    huella_dispositivo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    motivo: Mapped[str] = mapped_column(Text, default="")
    id_evento_origen: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)


class SolicitudAprobacionModel(Base):
    __tablename__ = "solicitud_aprobacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    accion: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    id_solicitante: Mapped[str] = mapped_column(String(64), index=True)
    rol_solicitante: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    id_aprobador: Mapped[str | None] = mapped_column(String(64), nullable=True)
    motivo_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_decision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParametroModel(Base):
    __tablename__ = "parametro"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[int] = mapped_column(Integer)


class AgenteMunicipalModel(Base):
    __tablename__ = "agente_municipal"

    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    rol: Mapped[str] = mapped_column(String(30))
