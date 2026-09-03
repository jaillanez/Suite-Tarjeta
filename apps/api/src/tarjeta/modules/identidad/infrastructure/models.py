"""Modelos SQLAlchemy del módulo identidad.

Datos sensibles (DNI, CUIL) con dos columnas: `_hash` (HMAC con pepper, único e
indexado) y `_cifrado` (AES-GCM, para recuperar el valor). El valor en claro no se
persiste en ninguna columna.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tarjeta.shared.infrastructure.database import Base


class PersonaModel(Base):
    __tablename__ = "persona"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    dni_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dni_cifrado: Mapped[str] = mapped_column(Text)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    cuil_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    cuil_cifrado: Mapped[str | None] = mapped_column(Text, nullable=True)
    apellido: Mapped[str] = mapped_column(String(120), default="")
    nombre: Mapped[str] = mapped_column(String(120), default="")
    celular: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    celular_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    estado_identidad: Mapped[str] = mapped_column(String(20))
    metodo_verificacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_alta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Lista de perfiles: [{"tipo": ..., "id_comercio": ..., "rol": ...}]
    perfiles: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)


class CredencialModel(Base):
    __tablename__ = "credencial"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona.id"), unique=True, index=True
    )
    hash: Mapped[str] = mapped_column(Text)


class DispositivoModel(Base):
    __tablename__ = "dispositivo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona.id"), index=True
    )
    nombre_declarado: Mapped[str] = mapped_column(String(120))
    plataforma: Mapped[str] = mapped_column(String(40))
    huella: Mapped[str] = mapped_column(String(128))
    fecha_alta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_ultimo_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20))
    autorizado_para_perfil_municipal: Mapped[bool] = mapped_column(Boolean, default=False)


class ConsentimientoModel(Base):
    __tablename__ = "consentimiento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(40))
    version_texto: Mapped[str] = mapped_column(String(20))
    otorgado: Mapped[bool] = mapped_column(Boolean)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str] = mapped_column(String(400))


class RefreshTokenModel(Base):
    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id_persona: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona.id"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    perfil: Mapped[str] = mapped_column(String(60))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)


class MfaModel(Base):
    __tablename__ = "mfa"

    id_persona: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona.id"), primary_key=True
    )
    secreto_cifrado: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=False)
    codigos_recuperacion: Mapped[list[str]] = mapped_column(JSONB, default=list)


class TextoLegalModel(Base):
    __tablename__ = "texto_legal"
    __table_args__ = (UniqueConstraint("tipo", "version", name="uq_texto_legal_tipo_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[str] = mapped_column(String(20))
    texto: Mapped[str] = mapped_column(Text)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)


# OutboxModel vive en shared/infrastructure/outbox.py (compartido entre módulos).
