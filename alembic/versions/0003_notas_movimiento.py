"""notas adicionales en movimientos (columna independiente)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04

Migración incremental y no destructiva: añade la columna ``notas``
(VARCHAR 500, anulable) a ``movimientos``. ``descripcion`` sigue siendo el
concepto del movimiento; ``notas`` guarda el detalle adicional opcional.
Las filas existentes quedan con ``notas = NULL`` (sin pérdida de datos).
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "movimientos",
        sa.Column("notas", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("movimientos", "notas")
