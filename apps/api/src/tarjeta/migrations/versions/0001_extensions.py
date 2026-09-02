"""Habilitar extensiones requeridas.

Revision ID: 0001_extensions
Revises:
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_extensions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EXTENSIONS = ("postgis", "pgcrypto", "pg_trgm", "btree_gist", "unaccent")


def upgrade() -> None:
    # IF NOT EXISTS: si el superusuario ya las creó en el alta de la base, es no-op.
    for ext in _EXTENSIONS:
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")


def downgrade() -> None:
    # No se eliminan: otras estructuras podrían depender de ellas.
    pass
