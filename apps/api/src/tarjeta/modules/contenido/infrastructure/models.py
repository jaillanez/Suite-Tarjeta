"""Modelos del módulo contenido. Las imágenes NO van acá: solo metadatos y claves del almacén."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class PiezaModel(Base):
    __tablename__ = "pieza"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_comercio: Mapped[str] = mapped_column(String(64), index=True)
    id_promocion: Mapped[str] = mapped_column(String(64), index=True)
    origen: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), index=True)
    plantilla: Mapped[str] = mapped_column(String(40))
    idea_texto: Mapped[str] = mapped_column(Text, default="")
    prompt_usado: Mapped[str] = mapped_column(Text, default="")
    superposicion: Mapped[dict[str, Any]] = mapped_column(JSONB)
    imagen_fondo_clave: Mapped[str] = mapped_column(String(200))
    variantes_claves: Mapped[list[str]] = mapped_column(JSONB, default=list)
    formatos: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    generada_por_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    modelo_ia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CreditoGeneracionModel(Base):
    """Cuota mensual por comercio y período (año-mes). `usados` se reserva atómicamente."""

    __tablename__ = "credito_generacion"

    id_comercio: Mapped[str] = mapped_column(String(64), primary_key=True)
    periodo: Mapped[str] = mapped_column(String(7), primary_key=True)  # YYYY-MM
    usados: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[int] = mapped_column(Integer, default=0)  # créditos extra de campañas
