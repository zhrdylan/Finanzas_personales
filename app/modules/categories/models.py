"""Modelo ORM del módulo categories: categorías de ingresos/gastos."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow

if TYPE_CHECKING:
    from app.modules.transactions.models import Transaction
    from app.modules.users.models import User


class Category(Base):
    """Categoría con la que se clasifican los movimientos.

    Ejemplos: Salario (ingreso), Alimentación (gasto). Cada categoría
    pertenece a un usuario (multitenancy por fila).
    """

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'ingreso' | 'gasto' (restringido también por CHECK en la BD)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    # Color hexadecimal, p. ej. '#3b82f6' (validado por Pydantic)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    # Icono (emoji o texto corto) mostrado en la interfaz
    icono: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    usuario: Mapped["User"] = relationship(back_populates="categorias")
    movimientos: Mapped[list["Transaction"]] = relationship(back_populates="categoria")

    __table_args__ = (
        # Un mismo usuario no puede repetir nombre dentro del mismo tipo
        UniqueConstraint("usuario_id", "nombre", "tipo", name="uq_categorias_usuario_nombre_tipo"),
        CheckConstraint("tipo IN ('ingreso', 'gasto')", name="ck_categorias_tipo"),
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} nombre={self.nombre!r} tipo={self.tipo!r}>"
