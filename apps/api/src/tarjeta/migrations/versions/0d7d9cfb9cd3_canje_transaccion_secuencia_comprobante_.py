"""canje: transaccion, secuencia comprobante; uso_promocion (topes usuario/dia)

Revision ID: 0d7d9cfb9cd3
Revises: 966f8497de23
Create Date: 2026-09-03

Incluye la deuda del PASO 07 (§08.0.A): tabla `uso_promocion` para el refuerzo atómico de los
topes por usuario y por día (el tope total sigue en `promocion.usos_totales`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0d7d9cfb9cd3"
down_revision: str | None = "966f8497de23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Deuda 08.0.A: usos por promoción, persona y fecha -------------------
    op.create_table(
        "uso_promocion",
        sa.Column("id_promocion", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_persona", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_promocion", "id_persona", "fecha"),
    )

    # --- Secuencia de comprobante (RIV-000000123) ----------------------------
    # Creada por el migrador; las DEFAULT PRIVILEGES otorgan USAGE a tarjeta_app.
    op.execute("CREATE SEQUENCE comprobante_seq START 1")

    # --- Transacciones -------------------------------------------------------
    op.create_table(
        "transaccion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_comprobante", sa.String(length=24), nullable=False),
        sa.Column("id_persona", sa.String(length=64), nullable=False),
        sa.Column("nivel_aplicado", sa.String(length=20), nullable=False),
        sa.Column("id_comercio", sa.String(length=64), nullable=False),
        sa.Column("id_sucursal", sa.String(length=64), nullable=False),
        sa.Column("id_cajero", sa.String(length=64), nullable=False),
        sa.Column("id_promocion", sa.String(length=64), nullable=True),
        sa.Column("monto_bruto", sa.Integer(), nullable=False),
        sa.Column("descuento", sa.Integer(), nullable=False),
        sa.Column("via", sa.String(length=30), nullable=False),
        sa.Column("confirmador", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("clave_idempotencia", sa.String(length=80), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sin_conexion", sa.Boolean(), nullable=False),
        sa.Column("geo_lat", sa.Float(), nullable=True),
        sa.Column("geo_lon", sa.Float(), nullable=True),
        sa.Column("distancia_m", sa.Float(), nullable=True),
        sa.Column("calificacion", sa.Integer(), nullable=True),
        sa.Column("motivo_anulacion", sa.Text(), nullable=True),
        sa.Column("en_disputa", sa.Boolean(), nullable=False),
        sa.Column("puntos_ciudadano", sa.Integer(), nullable=False),
        sa.Column("puntos_municipio", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_comprobante"),
        sa.UniqueConstraint("clave_idempotencia"),
    )
    op.create_index(
        op.f("ix_transaccion_numero_comprobante"),
        "transaccion",
        ["numero_comprobante"],
        unique=True,
    )
    op.create_index(op.f("ix_transaccion_id_persona"), "transaccion", ["id_persona"])
    op.create_index(op.f("ix_transaccion_id_comercio"), "transaccion", ["id_comercio"])
    op.create_index(op.f("ix_transaccion_id_sucursal"), "transaccion", ["id_sucursal"])
    op.create_index(op.f("ix_transaccion_id_cajero"), "transaccion", ["id_cajero"])
    op.create_index(op.f("ix_transaccion_estado"), "transaccion", ["estado"])
    op.create_index(
        op.f("ix_transaccion_clave_idempotencia"),
        "transaccion",
        ["clave_idempotencia"],
        unique=True,
    )
    op.create_index(op.f("ix_transaccion_creada_en"), "transaccion", ["creada_en"])


def downgrade() -> None:
    op.drop_index(op.f("ix_transaccion_creada_en"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_clave_idempotencia"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_estado"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_id_cajero"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_id_sucursal"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_id_comercio"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_id_persona"), table_name="transaccion")
    op.drop_index(op.f("ix_transaccion_numero_comprobante"), table_name="transaccion")
    op.drop_table("transaccion")
    op.execute("DROP SEQUENCE IF EXISTS comprobante_seq")
    op.drop_table("uso_promocion")
