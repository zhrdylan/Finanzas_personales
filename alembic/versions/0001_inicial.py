"""inicial: usuarios, categorias, movimientos y refresh_tokens

Revision ID: 0001
Revises:
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------- usuarios -------------------------------- #
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("nombre_completo", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(), nullable=False),
        sa.Column("actualizado", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_username"), "usuarios", ["username"], unique=True)
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)

    # -------------------------- refresh_tokens ----------------------------- #
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira", sa.DateTime(), nullable=False),
        sa.Column("revocado", sa.DateTime(), nullable=True),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_usuario_id"), "refresh_tokens", ["usuario_id"])
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)

    # ----------------------------- categorias ------------------------------ #
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("icono", sa.String(length=16), nullable=False),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("tipo IN ('ingreso', 'gasto')", name="ck_categorias_tipo"),
        sa.UniqueConstraint("usuario_id", "nombre", "tipo", name="uq_categorias_usuario_nombre_tipo"),
    )
    op.create_index(op.f("ix_categorias_usuario_id"), "categorias", ["usuario_id"])

    # ---------------------------- movimientos ------------------------------ #
    op.create_table(
        "movimientos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("metodo_pago", sa.String(length=20), nullable=False),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.Column("actualizado", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("tipo IN ('ingreso', 'gasto')", name="ck_movimientos_tipo"),
        sa.CheckConstraint("monto > 0", name="ck_movimientos_monto_positivo"),
        sa.CheckConstraint(
            "metodo_pago IN ('efectivo', 'tarjeta', 'transferencia', 'otro')",
            name="ck_movimientos_metodo_pago",
        ),
    )
    op.create_index(op.f("ix_movimientos_usuario_id"), "movimientos", ["usuario_id"])
    op.create_index(op.f("ix_movimientos_categoria_id"), "movimientos", ["categoria_id"])
    op.create_index("ix_movimientos_usuario_fecha", "movimientos", ["usuario_id", "fecha"])


def downgrade() -> None:
    op.drop_table("movimientos")
    op.drop_table("categorias")
    op.drop_table("refresh_tokens")
    op.drop_table("usuarios")
