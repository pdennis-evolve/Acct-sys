from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin


class Customer(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    __tablename__ = "customers"

    display_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)

    billing_address_line1: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    billing_address_line2: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    billing_city: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    billing_state: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    billing_postal_code: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    billing_country: Mapped[str | None] = mapped_column(db.String(100), nullable=True)

    shipping_address_line1: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    shipping_address_line2: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    shipping_state: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    shipping_postal_code: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    shipping_country: Mapped[str | None] = mapped_column(db.String(100), nullable=True)

    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    contacts = relationship(
        "CustomerContact", backref="customer", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self, include_contacts=True):
        d = {
            "id": self.id,
            "display_name": self.display_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "billing_address": {
                "line1": self.billing_address_line1,
                "line2": self.billing_address_line2,
                "city": self.billing_city,
                "state": self.billing_state,
                "postal_code": self.billing_postal_code,
                "country": self.billing_country,
            },
            "shipping_address": {
                "line1": self.shipping_address_line1,
                "line2": self.shipping_address_line2,
                "city": self.shipping_city,
                "state": self.shipping_state,
                "postal_code": self.shipping_postal_code,
                "country": self.shipping_country,
            },
            "notes": self.notes,
            "is_active": self.is_active,
        }
        if include_contacts:
            d["contacts"] = [c.to_dict() for c in self.contacts]
        return d


class CustomerContact(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "customer_contacts"

    customer_id: Mapped[str] = mapped_column(
        db.ForeignKey("customers.id"), nullable=False, index=True
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
