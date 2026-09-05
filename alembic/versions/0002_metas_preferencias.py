"""metas de ahorro y preferencias de usuario (moneda)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04

Migración incremental y no destructiva: crea las tablas ``metas`` y
``preferencias_usuario``. No toca las tablas existentes (usuarios,
refresh_tokens, categorias, movimientos), por lo que es segura sobre una
base de datos con datos.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------- metas --------------------------------- #
    op.create_table(
        "metas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("monto_objetivo", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("monto_actual", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.Column("actualizado", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("monto_objetivo > 0", name="ck_metas_objetivo_positivo"),
        sa.CheckConstraint("monto_actual >= 0", name="ck_metas_actual_no_negativo"),
    )
    op.create_index(op.f("ix_metas_usuario_id"), "metas", ["usuario_id"])

    # ------------------------ preferencias_usuario ------------------------- #
    op.create_table(
        "preferencias_usuario",
        sa.Column("usuario_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.Column("actualizado", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id"),
        sa.CheckConstraint(
            "moneda IN ('COP', 'USD', 'EUR')", name="ck_preferencias_moneda"
        ),
    )


def downgrade() -> None:
    op.drop_table("preferencias_usuario")
    op.drop_index(op.f("ix_metas_usuario_id"), table_name="metas")
    op.drop_table("metas")
