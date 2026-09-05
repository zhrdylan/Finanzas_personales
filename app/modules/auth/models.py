"""Modelo ORM del módulo auth: refresh tokens (sesiones persistentes)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class RefreshToken(Base):
    """Registro de un refresh token emitido.

    Solo se almacena el hash SHA-256 del token. Permite:
    - revocación (logout / logout de todos los dispositivos),
    - rotación de un solo uso en cada renovación,
    - invalidar todas las sesiones al cambiar la contraseña.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expira: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Fecha en que se revocó (None => token vigente)
    revocado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    usuario: Mapped["User"] = relationship(back_populates="refresh_tokens")  # noqa: F821
