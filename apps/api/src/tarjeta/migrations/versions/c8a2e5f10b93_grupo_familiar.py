"""grupo familiar: grupo, miembros, invitaciones, alertas antifraude

Revision ID: c8a2e5f10b93
Revises: b3f1c2a7d9e4
Create Date: 2026-09-04

Una persona, un grupo (§10.2): se refuerza a nivel base con un índice único parcial sobre
`miembro_grupo(id_persona)` que solo aplica a las filas ACTIVO (una baja no bloquea reingresar).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8a2e5f10b93"
down_revision: str | None = "b3f1c2a7d9e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grupo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_titular", sa.String(length=64), nullable=False),
        sa.Column("modo_billetera", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_grupo_id_titular"), "grupo", ["id_titular"])
    op.create_index(op.f("ix_grupo_estado"), "grupo", ["estado"])

    op.create_table(
        "miembro_grupo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_grupo", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_persona", sa.String(length=64), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fecha_alta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tope_mensual", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_miembro_grupo_id_grupo"), "miembro_grupo", ["id_grupo"])
    op.create_index(op.f("ix_miembro_grupo_id_persona"), "miembro_grupo", ["id_persona"])
    op.create_index(op.f("ix_miembro_grupo_estado"), "miembro_grupo", ["estado"])
    # Una persona, un grupo: único activo por persona (las bajas no cuentan).
    op.create_index(
        "uq_miembro_persona_activo",
        "miembro_grupo",
        ["id_persona"],
        unique=True,
        postgresql_where=sa.text("estado = 'ACTIVO'"),
    )

    op.create_table(
        "invitacion_grupo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_grupo", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("texto_declaracion", sa.Text(), nullable=False),
        sa.Column("id_titular", sa.String(length=64), nullable=False),
        sa.Column("ip_titular", sa.String(length=64), nullable=False),
        sa.Column("declarada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("aceptada_por", sa.String(length=64), nullable=True),
        sa.Column("aceptada_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_invitacion_grupo_id_grupo"), "invitacion_grupo", ["id_grupo"])
    op.create_index(op.f("ix_invitacion_grupo_token"), "invitacion_grupo", ["token"], unique=True)
    op.create_index(op.f("ix_invitacion_grupo_estado"), "invitacion_grupo", ["estado"])

    op.create_table(
        "alerta_grupo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_grupo", sa.String(length=64), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerta_grupo_id_grupo"), "alerta_grupo", ["id_grupo"])


def downgrade() -> None:
    op.drop_index(op.f("ix_alerta_grupo_id_grupo"), table_name="alerta_grupo")
    op.drop_table("alerta_grupo")
    op.drop_index(op.f("ix_invitacion_grupo_estado"), table_name="invitacion_grupo")
    op.drop_index(op.f("ix_invitacion_grupo_token"), table_name="invitacion_grupo")
    op.drop_index(op.f("ix_invitacion_grupo_id_grupo"), table_name="invitacion_grupo")
    op.drop_table("invitacion_grupo")
    op.drop_index("uq_miembro_persona_activo", table_name="miembro_grupo")
    op.drop_index(op.f("ix_miembro_grupo_estado"), table_name="miembro_grupo")
    op.drop_index(op.f("ix_miembro_grupo_id_persona"), table_name="miembro_grupo")
    op.drop_index(op.f("ix_miembro_grupo_id_grupo"), table_name="miembro_grupo")
    op.drop_table("miembro_grupo")
    op.drop_index(op.f("ix_grupo_estado"), table_name="grupo")
    op.drop_index(op.f("ix_grupo_id_titular"), table_name="grupo")
    op.drop_table("grupo")
