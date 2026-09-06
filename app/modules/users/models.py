"""Modelos ORM del módulo users: usuarios y sus preferencias."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow
from app.shared.moneda import MONEDA_POR_DEFECTO

if TYPE_CHECKING:  # solo para tipado, evita importaciones circulares
    from app.modules.auth.models import RefreshToken
    from app.modules.categories.models import Category
    from app.modules.goals.models import Meta
    from app.modules.transactions.models import Transaction


class User(Base):
    """Cuenta de usuario de la aplicación."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Nombre de usuario único (búsqueda frecuente => índice único)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # Correo único, almacenado en minúsculas
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(100), nullable=False)
    # Solo se persiste el hash bcrypt, JAMÁS la contraseña en claro.
    # Nullable: las cuentas creadas solo con Google no tienen contraseña.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Identificador de Google (claim `sub`): vincula la cuenta con Google.
    # Nullable y único (MySQL permite múltiples NULL en columna UNIQUE).
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Al eliminar el usuario se eliminan en cascada TODOS sus datos
    # (categorías, movimientos, metas, sesiones): requisito de privacidad.
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    categorias: Mapped[list["Category"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    movimientos: Mapped[list["Transaction"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    metas: Mapped[list["Meta"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    preferencia: Mapped["Preferencia | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )

    def __repr__(self) -> str:  # útil en logs de depuración
        return f"<User id={self.id} username={self.username!r}>"


class Preferencia(Base):
    """Preferencias de cuenta del usuario (una fila por usuario).

    Hoy almacena la moneda de visualización (COP | USD | EUR). La moneda NO
    convierte montos: solo define cómo se formatean en la interfaz.
    """

    __tablename__ = "preferencias_usuario"

    # Relación 1:1 con usuarios (PK = FK)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    moneda: Mapped[str] = mapped_column(String(3), default=MONEDA_POR_DEFECTO, nullable=False)
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    usuario: Mapped["User"] = relationship(back_populates="preferencia")

    __table_args__ = (
        CheckConstraint("moneda IN ('COP', 'USD', 'EUR')", name="ck_preferencias_moneda"),
    )

    def __repr__(self) -> str:
        return f"<Preferencia usuario_id={self.usuario_id} moneda={self.moneda!r}>"
