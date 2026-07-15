from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin


class CompanySettings(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """One row per tenant: legal name, billing identity, invoice numbering."""

    __tablename__ = "company_settings"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", name="uq_company_settings_tenant"),
    )

    company_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(db.String(500), nullable=True)

    fiscal_year_start_month: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)

    invoice_prefix: Mapped[str] = mapped_column(db.String(10), nullable=False, default="INV-")
    next_invoice_number: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1001)
    default_invoice_terms_days: Mapped[int] = mapped_column(db.Integer, nullable=False, default=30)

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
            "logo_url": self.logo_url,
            "fiscal_year_start_month": self.fiscal_year_start_month,
            "invoice_prefix": self.invoice_prefix,
            "next_invoice_number": self.next_invoice_number,
            "default_invoice_terms_days": self.default_invoice_terms_days,
        }
