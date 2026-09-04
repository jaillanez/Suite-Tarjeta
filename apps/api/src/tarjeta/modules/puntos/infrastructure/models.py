"""Modelos del módulo puntos."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class BilleteraModel(Base):
    __tablename__ = "billetera"
    __table_args__ = (
        UniqueConstraint(
            "tipo_titular",
            "id_titular",
            "tipo_moneda",
            "id_comercio",
            name="uq_billetera_titular_moneda_comercio",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tipo_titular: Mapped[str] = mapped_column(String(20))
    id_titular: Mapped[str] = mapped_column(String(64), index=True)
    tipo_moneda: Mapped[str] = mapped_column(String(4))
    # PC: comercio emisor; PM: centinela municipal ("").
    id_comercio: Mapped[str] = mapped_column(String(64), default="")
    saldo: Mapped[int] = mapped_column(Integer, default=0)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LotePuntosModel(Base):
    __tablename__ = "lote_puntos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_billetera: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    monto_original: Mapped[int] = mapped_column(Integer)
    saldo_restante: Mapped[int] = mapped_column(Integer)
    vence_en: Mapped[date] = mapped_column(Date, index=True)
    origen_puntos: Mapped[str] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    id_transaccion_canje: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vencido: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class MovimientoBilleteraModel(Base):
    """Libro contable append-only. `tarjeta_app` no tiene UPDATE/DELETE (se revoca en la
    migración, §09.2)."""

    __tablename__ = "movimiento_billetera"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_billetera: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    monto: Mapped[int] = mapped_column(Integer)
    origen_puntos: Mapped[str] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    id_lote: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    id_transaccion_canje: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    id_movimiento_original: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    clave_dedup: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    concepto: Mapped[str] = mapped_column(Text, default="")


class ItemCatalogoModel(Base):
    __tablename__ = "item_catalogo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    costo_pm: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    fecha_desde: Mapped[date] = mapped_column(Date)
    fecha_hasta: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ComprobanteInventarioModel(Base):
    __tablename__ = "comprobante_inventario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_item: Mapped[str] = mapped_column(String(64), index=True)
    id_persona: Mapped[str] = mapped_column(String(64), index=True)
    titulo_item: Mapped[str] = mapped_column(String(160))
    codigo: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    costo_pm: Mapped[int] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
