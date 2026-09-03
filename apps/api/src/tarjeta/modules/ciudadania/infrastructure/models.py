"""Modelos del módulo ciudadania."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class PerfilCiudadanoModel(Base):
    __tablename__ = "perfil_ciudadano"

    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    nivel: Mapped[str] = mapped_column(String(20))
    nivel_origen: Mapped[str] = mapped_column(String(20))
    numero_tarjeta: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    estado_tarjeta: Mapped[str] = mapped_column(String(20))
    tiene_tarjeta_fisica: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_ultimo_calculo: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HistorialNivelModel(Base):
    __tablename__ = "historial_nivel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    nivel_anterior: Mapped[str] = mapped_column(String(20))
    nivel_nuevo: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str] = mapped_column(String(60))
    detalle_regla_aplicada: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExcepcionNivelModel(Base):
    __tablename__ = "excepcion_nivel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    motivo: Mapped[str] = mapped_column(String(200))
    vigencia_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vigencia_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
