"""Modelo ORM del módulo exchange_rates: caché persistente de tasas.

Cada fila es una tasa diaria (base → quote) publicada por el proveedor.
La unicidad (base, quote, fecha) evita duplicados; la app NUNCA inventa
tasas: solo persiste las que devuelve Frankfurter v2.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class ExchangeRate(Base):
    """Tasa de cambio diaria almacenada (caché en MySQL)."""

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="frankfurter")
    creado: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            "rate_date",
            name="uq_tasas_base_quote_fecha",
        ),
        CheckConstraint("rate > 0", name="ck_tasas_rate_positivo"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExchangeRate {self.base_currency}->{self.quote_currency} "
            f"{self.rate} @ {self.rate_date}>"
        )
