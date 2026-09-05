"""Modelo ORM del módulo goals: metas de ahorro."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow

if TYPE_CHECKING:
    from app.modules.users.models import User


class Meta(Base):
    """Meta de ahorro de un usuario.

    El progreso se registra mediante aportes (``POST /metas/{id}/aportes``)
    que incrementan ``monto_actual``; el porcentaje y el estado se calculan
    a partir de ``monto_actual`` y ``monto_objetivo``.
    """

    __tablename__ = "metas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # Importes con DECIMAL(12,2) — NUNCA FLOAT — para dinero
    monto_objetivo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_actual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    # Fecha estimada de cumplimiento (opcional)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Moneda de la meta (COP/USD/EUR). Los aportes se registran en esta
    # moneda; la visualización en otra usa exchange_rates sin modificarla.
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    usuario: Mapped["User"] = relationship(back_populates="metas")

    __table_args__ = (
        Index("ix_metas_usuario_id", "usuario_id"),
        CheckConstraint("monto_objetivo > 0", name="ck_metas_objetivo_positivo"),
        CheckConstraint("monto_actual >= 0", name="ck_metas_actual_no_negativo"),
        CheckConstraint(
            "moneda IN ('COP', 'USD', 'EUR')",
            name="ck_metas_moneda",
        ),
    )

    def __repr__(self) -> str:
        return f"<Meta id={self.id} nombre={self.nombre!r} objetivo={self.monto_objetivo}>"
