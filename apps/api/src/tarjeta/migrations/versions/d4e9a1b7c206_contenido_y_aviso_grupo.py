"""contenido: piezas y cuota de generación; aviso de grupo (deuda §11.0.C)

Revision ID: d4e9a1b7c206
Revises: c8a2e5f10b93
Create Date: 2026-09-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e9a1b7c206"
down_revision: str | None = "c8a2e5f10b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Deuda §11.0.C: aviso al sucesor de titular -------------------------
    op.create_table(
        "aviso_grupo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_persona", sa.String(length=64), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("visto", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aviso_grupo_id_persona"), "aviso_grupo", ["id_persona"])
    op.create_index(op.f("ix_aviso_grupo_visto"), "aviso_grupo", ["visto"])

    # --- Piezas gráficas -----------------------------------------------------
    op.create_table(
        "pieza",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_comercio", sa.String(length=64), nullable=False),
        sa.Column("id_promocion", sa.String(length=64), nullable=False),
        sa.Column("origen", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("plantilla", sa.String(length=40), nullable=False),
        sa.Column("idea_texto", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_usado", sa.Text(), nullable=False, server_default=""),
        sa.Column("superposicion", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("imagen_fondo_clave", sa.String(length=200), nullable=False),
        sa.Column("variantes_claves", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("formatos", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generada_por_ia", sa.Boolean(), nullable=False),
        sa.Column("modelo_ia", sa.String(length=80), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pieza_id_comercio"), "pieza", ["id_comercio"])
    op.create_index(op.f("ix_pieza_id_promocion"), "pieza", ["id_promocion"])
    op.create_index(op.f("ix_pieza_estado"), "pieza", ["estado"])
    op.create_index(op.f("ix_pieza_creado_en"), "pieza", ["creado_en"])

    # --- Cuota de generación (reserva atómica) -------------------------------
    op.create_table(
        "credito_generacion",
        sa.Column("id_comercio", sa.String(length=64), nullable=False),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column("usados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id_comercio", "periodo"),
    )


def downgrade() -> None:
    op.drop_table("credito_generacion")
    op.drop_index(op.f("ix_pieza_creado_en"), table_name="pieza")
    op.drop_index(op.f("ix_pieza_estado"), table_name="pieza")
    op.drop_index(op.f("ix_pieza_id_promocion"), table_name="pieza")
    op.drop_index(op.f("ix_pieza_id_comercio"), table_name="pieza")
    op.drop_table("pieza")
    op.drop_index(op.f("ix_aviso_grupo_visto"), table_name="aviso_grupo")
    op.drop_index(op.f("ix_aviso_grupo_id_persona"), table_name="aviso_grupo")
    op.drop_table("aviso_grupo")
