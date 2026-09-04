"""promociones: promocion, topes, motor, confianza, favoritos; trigger latlon; f_unaccent

Revision ID: 966f8497de23
Revises: e92566b17711
Create Date: 2026-09-03

Incluye la deuda del PASO 06:
- §07.0.B: la ubicación de la sucursal tiene UNA sola fuente de verdad (`ubicacion`, geography);
  lat/lon se derivan por un trigger de base, así cualquier camino de actualización las deja
  coherentes.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "966f8497de23"
down_revision: str | None = "e92566b17711"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Deuda 07.0.B: lat/lon derivadas de `ubicacion` por trigger --------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sucursal_sync_latlon() RETURNS trigger AS $$
        BEGIN
            NEW.lat := ST_Y(NEW.ubicacion::geometry);
            NEW.lon := ST_X(NEW.ubicacion::geometry);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_sucursal_sync_latlon
        BEFORE INSERT OR UPDATE OF ubicacion ON sucursal
        FOR EACH ROW EXECUTE FUNCTION sucursal_sync_latlon();
        """
    )
    # Re-derivar las existentes para dejarlas coherentes de entrada.
    op.execute(
        "UPDATE sucursal SET lat = ST_Y(ubicacion::geometry), lon = ST_X(ubicacion::geometry)"
    )

    # --- Búsqueda sin tildes (§07.6): wrapper inmutable de unaccent -----------
    # unaccent(text) es STABLE; se envuelve en PL/pgSQL (no se inlinea) declarado IMMUTABLE,
    # para poder usarlo en un índice de expresión. Es la receta estándar.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE STRICT AS
        $$ BEGIN RETURN public.unaccent($1); END $$;
        """
    )

    # --- Promocion -----------------------------------------------------------
    op.create_table(
        "promocion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_comercio", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("mecanica", sa.String(length=30), nullable=False),
        sa.Column("segmento", sa.String(length=20), nullable=False),
        sa.Column("valor_platino", sa.Integer(), nullable=True),
        sa.Column("valor_black", sa.Integer(), nullable=False),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=False),
        sa.Column("dias_semana", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hora_desde", sa.Time(), nullable=True),
        sa.Column("hora_hasta", sa.Time(), nullable=True),
        sa.Column("acumulable", sa.Boolean(), nullable=False),
        sa.Column("destacada_municipal", sa.Boolean(), nullable=False),
        sa.Column("tope_total", sa.Integer(), nullable=True),
        sa.Column("tope_por_usuario", sa.Integer(), nullable=True),
        sa.Column("tope_por_dia", sa.Integer(), nullable=True),
        sa.Column("usos_totales", sa.Integer(), nullable=False),
        sa.Column("monto_minimo", sa.Integer(), nullable=False),
        sa.Column("imagen_url", sa.String(length=400), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_promocion_id_comercio"), "promocion", ["id_comercio"])
    op.create_index(op.f("ix_promocion_estado"), "promocion", ["estado"])
    op.create_index(op.f("ix_promocion_fecha_hasta"), "promocion", ["fecha_hasta"])
    op.create_index(op.f("ix_promocion_creada_en"), "promocion", ["creada_en"])
    # Índice compuesto pensado para el motor de resolución (§07.4).
    op.create_index("ix_promocion_motor", "promocion", ["estado", "fecha_desde", "fecha_hasta"])
    # Búsqueda por texto sin tildes (pg_trgm + f_unaccent).
    op.execute(
        "CREATE INDEX ix_promocion_texto_trgm ON promocion "
        "USING gin (f_unaccent(titulo || ' ' || descripcion) gin_trgm_ops)"
    )

    # --- Alcance por sucursal (tabla puente para el motor) -------------------
    op.create_table(
        "promocion_sucursal",
        sa.Column("id_promocion", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_sucursal", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id_promocion", "id_sucursal"),
    )
    op.create_index(
        op.f("ix_promocion_sucursal_id_sucursal"), "promocion_sucursal", ["id_sucursal"]
    )

    # --- Nivel de confianza del comercio (§07.5) -----------------------------
    op.create_table(
        "perfil_confianza_comercio",
        sa.Column("id_comercio", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nivel", sa.String(length=20), nullable=False),
        sa.Column("promos_aprobadas", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_comercio"),
    )

    # --- Favoritos (§07.6) ---------------------------------------------------
    op.create_table(
        "favorito",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_persona", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("valor", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_persona", "tipo", "valor", name="uq_favorito"),
    )
    op.create_index(op.f("ix_favorito_id_persona"), "favorito", ["id_persona"])


def downgrade() -> None:
    op.drop_index(op.f("ix_favorito_id_persona"), table_name="favorito")
    op.drop_table("favorito")
    op.drop_table("perfil_confianza_comercio")
    op.drop_index(op.f("ix_promocion_sucursal_id_sucursal"), table_name="promocion_sucursal")
    op.drop_table("promocion_sucursal")
    op.execute("DROP INDEX IF EXISTS ix_promocion_texto_trgm")
    op.drop_index("ix_promocion_motor", table_name="promocion")
    op.drop_index(op.f("ix_promocion_creada_en"), table_name="promocion")
    op.drop_index(op.f("ix_promocion_fecha_hasta"), table_name="promocion")
    op.drop_index(op.f("ix_promocion_estado"), table_name="promocion")
    op.drop_index(op.f("ix_promocion_id_comercio"), table_name="promocion")
    op.drop_table("promocion")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
    op.execute("DROP TRIGGER IF EXISTS trg_sucursal_sync_latlon ON sucursal")
    op.execute("DROP FUNCTION IF EXISTS sucursal_sync_latlon()")
