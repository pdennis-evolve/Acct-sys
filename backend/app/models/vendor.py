from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin


class Vendor(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    __tablename__ = "vendors"

    display_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)

    address_line1: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(db.String(100), nullable=True)

    default_expense_account_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("accounts.id"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    contacts = relationship(
        "VendorContact", backref="vendor", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self, include_contacts=True):
        d = {
            "id": self.id,
            "display_name": self.display_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "postal_code": self.postal_code,
                "country": self.country,
            },
            "default_expense_account_id": self.default_expense_account_id,
            "notes": self.notes,
            "is_active": self.is_active,
        }
        if include_contacts:
            d["contacts"] = [c.to_dict() for c in self.contacts]
        return d


class VendorContact(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "vendor_contacts"

    vendor_id: Mapped[str] = mapped_column(
        db.ForeignKey("vendors.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    title: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    is_primary: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "phone": self.phone,
            "is_primary": self.is_primary,
        }
