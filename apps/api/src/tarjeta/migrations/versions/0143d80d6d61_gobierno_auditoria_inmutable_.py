"""gobierno: auditoria inmutable, aprobaciones, parametria, agentes; outbox reintentos

Revision ID: 0143d80d6d61
Revises: c47f26a79e51
Create Date: 2026-09-03

Inmutabilidad a nivel DB (§05.4): las tablas creadas por `tarjeta_migrator` reciben
`arwd` para `tarjeta_app` vía DEFAULT PRIVILEGES. Sobre `registro_auditoria` se revocan
UPDATE y DELETE; como `tarjeta_app` no es dueño de la tabla, no puede volver a otorgárselos,
de modo que en runtime solo puede INSERTAR y LEER auditoría (nunca modificar ni borrar).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0143d80d6d61"
down_revision: str | None = "c47f26a79e51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Rol de runtime al que se le restringe la modificación de auditoría.
_ROL_APP = "tarjeta_app"


def upgrade() -> None:
    # --- Auditoría inmutable -------------------------------------------------
    op.create_table(
        "registro_auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_persona_actor", sa.String(length=64), nullable=True),
        sa.Column("rol_actor", sa.String(length=30), nullable=True),
        sa.Column("perfil_activo", sa.String(length=60), nullable=True),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("entidad", sa.String(length=60), nullable=False),
        sa.Column("id_entidad", sa.String(length=64), nullable=False),
        sa.Column("valor_anterior", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valor_nuevo", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=400), nullable=False),
        sa.Column("huella_dispositivo", sa.String(length=128), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("id_evento_origen", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_evento_origen"),
    )
    op.create_index(
        op.f("ix_registro_auditoria_timestamp"), "registro_auditoria", ["timestamp"], unique=False
    )
    op.create_index(
        op.f("ix_registro_auditoria_id_persona_actor"),
        "registro_auditoria",
        ["id_persona_actor"],
        unique=False,
    )
    op.create_index(
        op.f("ix_registro_auditoria_accion"), "registro_auditoria", ["accion"], unique=False
    )
    op.create_index(
        op.f("ix_registro_auditoria_entidad"), "registro_auditoria", ["entidad"], unique=False
    )
    # Inmutabilidad a nivel motor: el rol de runtime solo INSERTA y LEE auditoría.
    op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON registro_auditoria FROM {_ROL_APP}")

    # --- Doble conformidad ---------------------------------------------------
    op.create_table(
        "solicitud_aprobacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id_solicitante", sa.String(length=64), nullable=False),
        sa.Column("rol_solicitante", sa.String(length=30), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fecha_solicitud", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_aprobador", sa.String(length=64), nullable=True),
        sa.Column("motivo_decision", sa.Text(), nullable=True),
        sa.Column("fecha_decision", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_solicitud_aprobacion_id_solicitante"),
        "solicitud_aprobacion",
        ["id_solicitante"],
        unique=False,
    )
    op.create_index(
        op.f("ix_solicitud_aprobacion_estado"), "solicitud_aprobacion", ["estado"], unique=False
    )

    # --- Parametría ----------------------------------------------------------
    op.create_table(
        "parametro",
        sa.Column("clave", sa.String(length=60), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("clave"),
    )

    # --- Agentes municipales -------------------------------------------------
    op.create_table(
        "agente_municipal",
        sa.Column("id_persona", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id_persona"),
    )

    # --- Outbox: reintentos, backoff y cola de muertos (§05.1) ---------------
    op.add_column("outbox", sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("outbox", sa.Column("proximo_intento", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "outbox",
        sa.Column("muerto", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("outbox", sa.Column("error", sa.Text(), nullable=True))
    op.create_index(op.f("ix_outbox_muerto"), "outbox", ["muerto"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_muerto"), table_name="outbox")
    op.drop_column("outbox", "error")
    op.drop_column("outbox", "muerto")
    op.drop_column("outbox", "proximo_intento")
    op.drop_column("outbox", "intentos")

    op.drop_table("agente_municipal")
    op.drop_table("parametro")
    op.drop_index(op.f("ix_solicitud_aprobacion_estado"), table_name="solicitud_aprobacion")
    op.drop_index(op.f("ix_solicitud_aprobacion_id_solicitante"), table_name="solicitud_aprobacion")
    op.drop_table("solicitud_aprobacion")

    op.drop_index(op.f("ix_registro_auditoria_entidad"), table_name="registro_auditoria")
    op.drop_index(op.f("ix_registro_auditoria_accion"), table_name="registro_auditoria")
    op.drop_index(op.f("ix_registro_auditoria_id_persona_actor"), table_name="registro_auditoria")
    op.drop_index(op.f("ix_registro_auditoria_timestamp"), table_name="registro_auditoria")
    op.drop_table("registro_auditoria")
