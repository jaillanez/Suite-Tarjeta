"""identidad: reetiquetar metodo_verificacion RENAPER -> AUTODECLARADA (§12.2-C)

Revision ID: e1f3b9c7a840
Revises: d4e9a1b7c206
Create Date: 2026-09-04

Los registros existentes quedaron mal etiquetados como `RENAPER` sin haberlo consultado (además
está fuera de alcance). Se corrigen a `AUTODECLARADA`, el estado real del alta por la app.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e1f3b9c7a840"
down_revision: str | None = "d4e9a1b7c206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE persona SET metodo_verificacion = 'AUTODECLARADA' "
        "WHERE metodo_verificacion = 'RENAPER'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE persona SET metodo_verificacion = 'RENAPER' "
        "WHERE metodo_verificacion = 'AUTODECLARADA'"
    )
