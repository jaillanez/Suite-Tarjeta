"""Modelos del módulo padron (§7.5). No existen columnas de monto/cuenta/cuota/vencimiento."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class EstadoPadronModel(Base):
    __tablename__ = "estado_padron"

    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    dni_cifrado: Mapped[str] = mapped_column(Text)
    al_dia: Mapped[bool] = mapped_column(Boolean, default=False)
    es_comerciante: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_ultima_consulta: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HistorialEstadoPadronModel(Base):
    __tablename__ = "historial_estado_padron"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    campo: Mapped[str] = mapped_column(String(40))
    valor_anterior: Mapped[str] = mapped_column(String(40))
    valor_nuevo: Mapped[str] = mapped_column(String(40))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origen_consulta: Mapped[str] = mapped_column(String(20))
