"""puntos: billeteras, libro append-only, lotes FIFO, inventario municipal

Revision ID: b3f1c2a7d9e4
Revises: 0d7d9cfb9cd3
Create Date: 2026-09-04

Libro contable inmutable (§09.2): `movimiento_billetera` es append-only. Igual que la auditoría
del PASO 05, se revoca UPDATE/DELETE/TRUNCATE al rol de runtime `tarjeta_app`; como no es dueño
de la tabla, no puede volver a otorgárselos, de modo que en runtime solo INSERTA y LEE el libro.

También completa la deuda del canje: agrega a `transaccion` los puntos que consume el ciudadano
en la operación y los pesos que esos puntos cubren (§09.4).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3f1c2a7d9e4"
down_revision: str | None = "0d7d9cfb9cd3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROL_APP = "tarjeta_app"


def upgrade() -> None:
    # --- Billeteras (titular persona o grupo; una por moneda y comercio) ------
    op.create_table(
        "billetera",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_titular", sa.String(length=20), nullable=False),
        sa.Column("id_titular", sa.String(length=64), nullable=False),
        sa.Column("tipo_moneda", sa.String(length=4), nullable=False),
        sa.Column("id_comercio", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("saldo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tipo_titular",
            "id_titular",
            "tipo_moneda",
            "id_comercio",
            name="uq_billetera_titular_moneda_comercio",
        ),
    )
    op.create_index(op.f("ix_billetera_id_titular"), "billetera", ["id_titular"])

    # --- Lotes de puntos (vencimiento propio, consumo FIFO) ------------------
    op.create_table(
        "lote_puntos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_billetera", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monto_original", sa.Integer(), nullable=False),
        sa.Column("saldo_restante", sa.Integer(), nullable=False),
        sa.Column("vence_en", sa.Date(), nullable=False),
        sa.Column("origen_puntos", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_transaccion_canje", sa.String(length=64), nullable=True),
        sa.Column("vencido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lote_puntos_id_billetera"), "lote_puntos", ["id_billetera"])
    op.create_index(op.f("ix_lote_puntos_vence_en"), "lote_puntos", ["vence_en"])
    op.create_index(op.f("ix_lote_puntos_vencido"), "lote_puntos", ["vencido"])

    # --- Libro contable append-only ------------------------------------------
    op.create_table(
        "movimiento_billetera",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_billetera", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("monto", sa.Integer(), nullable=False),
        sa.Column("origen_puntos", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_lote", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id_transaccion_canje", sa.String(length=64), nullable=True),
        sa.Column("id_movimiento_original", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clave_dedup", sa.String(length=120), nullable=True),
        sa.Column("concepto", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clave_dedup"),
    )
    op.create_index(
        op.f("ix_movimiento_billetera_id_billetera"), "movimiento_billetera", ["id_billetera"]
    )
    op.create_index(
        op.f("ix_movimiento_billetera_creado_en"), "movimiento_billetera", ["creado_en"]
    )
    op.create_index(
        op.f("ix_movimiento_billetera_id_transaccion_canje"),
        "movimiento_billetera",
        ["id_transaccion_canje"],
    )
    # Inmutabilidad a nivel motor: el rol de runtime solo INSERTA y LEE el libro (§09.2).
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{_ROL_APP}') THEN
                REVOKE UPDATE, DELETE, TRUNCATE ON movimiento_billetera FROM {_ROL_APP};
            END IF;
        END$$;
        """
    )

    # --- Inventario municipal (catálogo + comprobantes) ----------------------
    op.create_table(
        "item_catalogo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False, server_default=""),
        sa.Column("costo_pm", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_catalogo_estado"), "item_catalogo", ["estado"])
    op.create_table(
        "comprobante_inventario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_item", sa.String(length=64), nullable=False),
        sa.Column("id_persona", sa.String(length=64), nullable=False),
        sa.Column("titulo_item", sa.String(length=160), nullable=False),
        sa.Column("codigo", sa.String(length=32), nullable=False),
        sa.Column("costo_pm", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index(
        op.f("ix_comprobante_inventario_id_item"), "comprobante_inventario", ["id_item"]
    )
    op.create_index(
        op.f("ix_comprobante_inventario_id_persona"), "comprobante_inventario", ["id_persona"]
    )
    op.create_index(
        op.f("ix_comprobante_inventario_codigo"),
        "comprobante_inventario",
        ["codigo"],
        unique=True,
    )

    # --- Deuda del canje: puntos que consume el ciudadano en la operación ----
    op.add_column(
        "transaccion",
        sa.Column("puntos_consumidos", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "transaccion",
        sa.Column("pesos_cubiertos_puntos", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("transaccion", "pesos_cubiertos_puntos")
    op.drop_column("transaccion", "puntos_consumidos")

    op.drop_index(op.f("ix_comprobante_inventario_codigo"), table_name="comprobante_inventario")
    op.drop_index(op.f("ix_comprobante_inventario_id_persona"), table_name="comprobante_inventario")
    op.drop_index(op.f("ix_comprobante_inventario_id_item"), table_name="comprobante_inventario")
    op.drop_table("comprobante_inventario")
    op.drop_index(op.f("ix_item_catalogo_estado"), table_name="item_catalogo")
    op.drop_table("item_catalogo")

    op.drop_index(
        op.f("ix_movimiento_billetera_id_transaccion_canje"), table_name="movimiento_billetera"
    )
    op.drop_index(op.f("ix_movimiento_billetera_creado_en"), table_name="movimiento_billetera")
    op.drop_index(op.f("ix_movimiento_billetera_id_billetera"), table_name="movimiento_billetera")
    op.drop_table("movimiento_billetera")

    op.drop_index(op.f("ix_lote_puntos_vencido"), table_name="lote_puntos")
    op.drop_index(op.f("ix_lote_puntos_vence_en"), table_name="lote_puntos")
    op.drop_index(op.f("ix_lote_puntos_id_billetera"), table_name="lote_puntos")
    op.drop_table("lote_puntos")

    op.drop_index(op.f("ix_billetera_id_titular"), table_name="billetera")
    op.drop_table("billetera")
