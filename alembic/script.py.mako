"""Plantilla para nuevas revisiones de Alembic."""

revision: str
down_revision
branch_labels
depends_on


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
