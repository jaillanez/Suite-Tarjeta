"""Comercio: columnas precarga y origen (§13.3).

`precarga` marca los comercios sembrados por el comando de carga (no adhesiones reales), para
identificarlos y darlos de baja en bloque. `origen` guarda de dónde salió el dato y cuándo.

Revision ID: c7f2a1b9d340
Revises: a3d5c7e91b02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c7f2a1b9d340"
down_revision = "a3d5c7e91b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comercio",
        sa.Column("precarga", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("comercio", sa.Column("origen", sa.String(length=300), nullable=True))
    op.create_index(op.f("ix_comercio_precarga"), "comercio", ["precarga"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comercio_precarga"), table_name="comercio")
    op.drop_column("comercio", "origen")
    op.drop_column("comercio", "precarga")
