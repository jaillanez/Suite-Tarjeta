"""Modelos del módulo canje."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class TransaccionModel(Base):
    __tablename__ = "transaccion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    numero_comprobante: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    id_persona: Mapped[str] = mapped_column(String(64), index=True)
    nivel_aplicado: Mapped[str] = mapped_column(String(20))
    id_comercio: Mapped[str] = mapped_column(String(64), index=True)
    id_sucursal: Mapped[str] = mapped_column(String(64), index=True)
    id_cajero: Mapped[str] = mapped_column(String(64), index=True)
    id_promocion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    monto_bruto: Mapped[int] = mapped_column(Integer)
    descuento: Mapped[int] = mapped_column(Integer)
    via: Mapped[str] = mapped_column(String(30))
    confirmador: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(30), index=True)
    clave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    vence_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confirmada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sin_conexion: Mapped[bool] = mapped_column(Boolean, default=False)
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    distancia_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    calificacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    en_disputa: Mapped[bool] = mapped_column(Boolean, default=False)
    # §08.1: presentes y en cero hasta el módulo puntos.
    puntos_ciudadano: Mapped[int] = mapped_column(Integer, default=0)
    puntos_municipio: Mapped[int] = mapped_column(Integer, default=0)
