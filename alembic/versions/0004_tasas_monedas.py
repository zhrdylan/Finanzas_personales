"""tasas de cambio y moneda en movimientos/metas

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05

Migración incremental y no destructiva (Fase 2: multi-moneda real):

* Crea la tabla ``exchange_rates`` (caché persistente de Frankfurter v2):
  clave única (base, quote, fecha) para no duplicar registros.
* Añade ``moneda`` (CHAR 3, NOT NULL, default 'COP', CHECK COP/USD/EUR)
  a ``movimientos`` y ``metas``. Las filas existentes quedan en COP
  (moneda histórica de la app: solo-display hasta ahora), sin pérdida
  de datos ni alteración de montos.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --------------------------- exchange_rates ---------------------------- #
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("creado", sa.DateTime(), nullable=False),
        sa.Column("actualizado", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rate > 0", name="ck_tasas_rate_positivo"),
        sa.UniqueConstraint(
            "base_currency",
            "quote_currency",
            "rate_date",
            name="uq_tasas_base_quote_fecha",
        ),
    )

    # --------------------- moneda en movimientos/metas --------------------- #
    # NOT NULL con DEFAULT 'COP': MySQL rellena las filas existentes con COP.
    op.add_column(
        "movimientos",
        sa.Column(
            "moneda",
            sa.String(length=3),
            nullable=False,
            server_default="COP",
        ),
    )
    op.create_check_constraint(
        "ck_movimientos_moneda",
        "movimientos",
        "moneda IN ('COP', 'USD', 'EUR')",
    )

    op.add_column(
        "metas",
        sa.Column(
            "moneda",
            sa.String(length=3),
            nullable=False,
            server_default="COP",
        ),
    )
    op.create_check_constraint(
        "ck_metas_moneda",
        "metas",
        "moneda IN ('COP', 'USD', 'EUR')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_metas_moneda", "metas", type_="check")
    op.drop_column("metas", "moneda")
    op.drop_constraint("ck_movimientos_moneda", "movimientos", type_="check")
    op.drop_column("movimientos", "moneda")
    op.drop_table("exchange_rates")
