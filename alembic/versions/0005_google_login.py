"""inicio de sesión con Google

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06

Migración incremental y no destructiva (inicio con Google):

* Añade ``usuarios.google_sub`` (VARCHAR 255, UNIQUE, NULL): identificador
  de Google (claim ``sub``). NULL para las cuentas existentes (MySQL
  permite múltiples NULL en columna UNIQUE).
* ``usuarios.hashed_password`` pasa a NULL: las cuentas creadas solo con
  Google no tienen contraseña. Las filas existentes conservan su hash.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("google_sub", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint("uq_usuarios_google_sub", "usuarios", ["google_sub"])
    op.alter_column(
        "usuarios",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "usuarios",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_constraint("uq_usuarios_google_sub", "usuarios", type_="unique")
    op.drop_column("usuarios", "google_sub")
