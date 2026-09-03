"""comercios: adhesion, sucursales PostGIS, usuarios, turnos; agente activo; vistas recaudacion

Revision ID: e92566b17711
Revises: 0143d80d6d61
Create Date: 2026-09-03

Incluye la deuda del PASO 05:
- `agente_municipal.activo` (§06.0.B): al revocar el perfil municipal en identidad, el agente
  se desactiva por evento.
- Vistas `vista_recaudacion_*` (§06.0.C): encapsulan la lectura cross-módulo de la métrica de
  recaudación; si otro módulo cambia su esquema, la vista rompe de forma ruidosa.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "e92566b17711"
down_revision: str | None = "0143d80d6d61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Deuda 06.0.B: agente municipal activable ----------------------------
    op.add_column(
        "agente_municipal",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # --- Comercio ------------------------------------------------------------
    op.create_table(
        "comercio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cuit", sa.String(length=13), nullable=False),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("nombre_fantasia", sa.String(length=200), nullable=False),
        sa.Column("rubro", sa.String(length=80), nullable=False),
        sa.Column("logo_url", sa.String(length=400), nullable=False),
        sa.Column("id_responsable", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("convenio_version", sa.String(length=20), nullable=True),
        sa.Column("convenio_fecha", sa.DateTime(timezone=True), nullable=True),
        sa.Column("convenio_ip", sa.String(length=64), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cuit"),
    )
    op.create_index(op.f("ix_comercio_cuit"), "comercio", ["cuit"], unique=True)
    op.create_index(op.f("ix_comercio_id_responsable"), "comercio", ["id_responsable"])
    op.create_index(op.f("ix_comercio_estado"), "comercio", ["estado"])

    # --- Sucursal (PostGIS geography + índice GiST, §06.3) -------------------
    op.create_table(
        "sucursal",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_comercio", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("direccion", sa.String(length=300), nullable=False),
        sa.Column("telefono", sa.String(length=40), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column(
            "ubicacion",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("es_casa_central", sa.Boolean(), nullable=False),
        sa.Column("horarios", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fotos", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("qr_token", sa.Text(), nullable=False),
        sa.Column("motivo_cierre", sa.Text(), nullable=False),
        sa.Column("reapertura_estimada", sa.String(length=40), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sucursal_id_comercio"), "sucursal", ["id_comercio"])
    op.create_index(op.f("ix_sucursal_estado"), "sucursal", ["estado"])
    op.create_index(
        "ix_sucursal_ubicacion_gist",
        "sucursal",
        ["ubicacion"],
        postgresql_using="gist",
    )

    # --- Usuario del comercio ------------------------------------------------
    op.create_table(
        "usuario_comercio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_comercio", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_persona", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.Column("sucursales", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("pin_hash", sa.Text(), nullable=True),
        sa.Column("huella_dispositivo", sa.String(length=128), nullable=True),
        sa.Column("pin_intentos", sa.Integer(), nullable=False),
        sa.Column("pin_bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuario_comercio_id_comercio"), "usuario_comercio", ["id_comercio"])
    op.create_index(op.f("ix_usuario_comercio_id_persona"), "usuario_comercio", ["id_persona"])
    op.create_index(op.f("ix_usuario_comercio_estado"), "usuario_comercio", ["estado"])

    # --- Invitación ----------------------------------------------------------
    op.create_table(
        "invitacion_comercio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_comercio", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.Column("sucursales", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("destino", sa.String(length=200), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_invitacion_comercio_id_comercio"), "invitacion_comercio", ["id_comercio"]
    )
    op.create_index(
        op.f("ix_invitacion_comercio_token_hash"),
        "invitacion_comercio",
        ["token_hash"],
        unique=True,
    )
    op.create_index(op.f("ix_invitacion_comercio_estado"), "invitacion_comercio", ["estado"])

    # --- Turno ---------------------------------------------------------------
    op.create_table(
        "turno_comercio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_sucursal", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_cajero", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("abierto_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resumen", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_turno_comercio_id_sucursal"), "turno_comercio", ["id_sucursal"])
    op.create_index(op.f("ix_turno_comercio_id_cajero"), "turno_comercio", ["id_cajero"])

    # --- Deuda 06.0.C: vistas de recaudación (encapsulan el SQL cross-módulo) ---
    op.execute(
        """
        CREATE VIEW vista_recaudacion_transiciones AS
        SELECT count(*)::bigint AS total
        FROM historial_estado_padron
        WHERE campo = 'al_dia' AND valor_nuevo = 'True'
        """
    )
    op.execute(
        """
        CREATE VIEW vista_recaudacion_por_nivel AS
        SELECT nivel, count(*)::bigint AS total
        FROM perfil_ciudadano
        GROUP BY nivel
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vista_recaudacion_por_nivel")
    op.execute("DROP VIEW IF EXISTS vista_recaudacion_transiciones")

    op.drop_index(op.f("ix_turno_comercio_id_cajero"), table_name="turno_comercio")
    op.drop_index(op.f("ix_turno_comercio_id_sucursal"), table_name="turno_comercio")
    op.drop_table("turno_comercio")

    op.drop_index(op.f("ix_invitacion_comercio_estado"), table_name="invitacion_comercio")
    op.drop_index(op.f("ix_invitacion_comercio_token_hash"), table_name="invitacion_comercio")
    op.drop_index(op.f("ix_invitacion_comercio_id_comercio"), table_name="invitacion_comercio")
    op.drop_table("invitacion_comercio")

    op.drop_index(op.f("ix_usuario_comercio_estado"), table_name="usuario_comercio")
    op.drop_index(op.f("ix_usuario_comercio_id_persona"), table_name="usuario_comercio")
    op.drop_index(op.f("ix_usuario_comercio_id_comercio"), table_name="usuario_comercio")
    op.drop_table("usuario_comercio")

    op.drop_index("ix_sucursal_ubicacion_gist", table_name="sucursal")
    op.drop_index(op.f("ix_sucursal_estado"), table_name="sucursal")
    op.drop_index(op.f("ix_sucursal_id_comercio"), table_name="sucursal")
    op.drop_table("sucursal")

    op.drop_index(op.f("ix_comercio_estado"), table_name="comercio")
    op.drop_index(op.f("ix_comercio_id_responsable"), table_name="comercio")
    op.drop_index(op.f("ix_comercio_cuit"), table_name="comercio")
    op.drop_table("comercio")

    op.drop_column("agente_municipal", "activo")
