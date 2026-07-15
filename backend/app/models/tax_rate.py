from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin


class TaxRate(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, db.Model):
    """Sales tax rate a tenant can apply to invoices. Persisted per-invoice
    (not just a request-time percentage) so sales tax reports can break
    collected tax out by jurisdiction after the fact."""

    __tablename__ = "tax_rates"

    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    rate: Mapped[Decimal] = mapped_column(db.Numeric(6, 4), nullable=False, default=0)
    jurisdiction: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rate": str(self.rate),
            "jurisdiction": self.jurisdiction,
            "is_default": self.is_default,
            "is_active": self.is_active,
        }
