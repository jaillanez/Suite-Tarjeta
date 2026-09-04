"""Modelos del módulo promociones."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class PromocionModel(Base):
    __tablename__ = "promocion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_comercio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    titulo: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    mecanica: Mapped[str] = mapped_column(String(30))
    segmento: Mapped[str] = mapped_column(String(20))
    valor_platino: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_black: Mapped[int] = mapped_column(Integer)
    fecha_desde: Mapped[date] = mapped_column(Date)
    fecha_hasta: Mapped[date] = mapped_column(Date, index=True)
    dias_semana: Mapped[list[int]] = mapped_column(JSONB, default=list)
    hora_desde: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_hasta: Mapped[time | None] = mapped_column(Time, nullable=True)
    acumulable: Mapped[bool] = mapped_column(Boolean, default=False)
    destacada_municipal: Mapped[bool] = mapped_column(Boolean, default=False)
    tope_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tope_por_usuario: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tope_por_dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usos_totales: Mapped[int] = mapped_column(Integer, default=0)
    monto_minimo: Mapped[int] = mapped_column(Integer, default=0)
    imagen_url: Mapped[str] = mapped_column(String(400), default="")
    estado: Mapped[str] = mapped_column(String(20), index=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PromocionSucursalModel(Base):
    __tablename__ = "promocion_sucursal"

    id_promocion: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_sucursal: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True)


class PerfilConfianzaModel(Base):
    __tablename__ = "perfil_confianza_comercio"

    id_comercio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    nivel: Mapped[str] = mapped_column(String(20))
    promos_aprobadas: Mapped[int] = mapped_column(Integer, default=0)


class FavoritoModel(Base):
    __tablename__ = "favorito"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # 'comercio' | 'rubro'
    valor: Mapped[str] = mapped_column(String(80))
