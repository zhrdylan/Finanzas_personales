"""Modelo ORM del módulo transactions: movimientos financieros."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow

if TYPE_CHECKING:
    from app.modules.categories.models import Category
    from app.modules.users.models import User


class Transaction(Base):
    """Movimiento financiero individual (ingreso o gasto).

    Nota de diseño: el campo ``tipo`` duplica el tipo de su categoría. Es una
    desnormalización consciente (evita un JOIN en cada consulta de totales);
    la consistencia se garantiza a nivel de aplicación (Pydantic + servicio:
    el tipo del movimiento debe coincidir con el de su categoría).

    El monto usa DECIMAL(12,2) — NUNCA FLOAT — para importes monetarios.
    """

    __tablename__ = "movimientos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    # RESTRICT: no se puede borrar una categoría con movimientos asociados;
    # el servicio lo comprueba antes y devuelve un 409 explicativo.
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # 'ingreso' | 'gasto'
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Notas adicionales opcionales (concepto va en `descripcion`).
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    # Moneda original del registro (COP/USD/EUR). La visualización en otra
    # moneda se resuelve con el módulo exchange_rates, sin tocar este valor.
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    metodo_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    usuario: Mapped["User"] = relationship(back_populates="movimientos")
    categoria: Mapped["Category"] = relationship(back_populates="movimientos")

    __table_args__ = (
        # Índice compuesto (usuario, fecha): soporta los rangos del dashboard
        Index("ix_movimientos_usuario_fecha", "usuario_id", "fecha"),
        CheckConstraint("tipo IN ('ingreso', 'gasto')", name="ck_movimientos_tipo"),
        CheckConstraint("monto > 0", name="ck_movimientos_monto_positivo"),
        CheckConstraint(
            "moneda IN ('COP', 'USD', 'EUR')",
            name="ck_movimientos_moneda",
        ),
        CheckConstraint(
            "metodo_pago IN ('efectivo', 'tarjeta', 'transferencia', 'otro')",
            name="ck_movimientos_metodo_pago",
        ),
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} tipo={self.tipo!r} monto={self.monto}>"
