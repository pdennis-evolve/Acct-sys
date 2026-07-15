from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

VENDOR_PAYMENT_METHODS = ["cash", "check", "credit_card", "ach", "other"]


class VendorPayment(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Money paid out to a vendor, applied across one or more approved
    bills. Mirrors Payment/PaymentApplication on the AR side."""

    __tablename__ = "vendor_payments"

    vendor_id: Mapped[str] = mapped_column(
        db.ForeignKey("vendors.id"), nullable=False, index=True
    )
    cash_account_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("cash_accounts.id"), nullable=True
    )
    payment_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(db.String(20), nullable=False, default="check")
    reference_number: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    memo: Mapped[str | None] = mapped_column(db.String(500), nullable=True)

    applications = relationship(
        "VendorPaymentApplication", backref="vendor_payment", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def amount_applied(self) -> Decimal:
        return sum((a.amount_applied for a in self.applications), Decimal("0"))

    @property
    def amount_unapplied(self) -> Decimal:
        return self.amount - self.amount_applied

    def to_dict(self):
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "cash_account_id": self.cash_account_id,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "amount": str(self.amount),
            "method": self.method,
            "reference_number": self.reference_number,
            "memo": self.memo,
            "amount_applied": str(self.amount_applied),
            "amount_unapplied": str(self.amount_unapplied),
            "applications": [a.to_dict() for a in self.applications],
        }


class VendorPaymentApplication(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "vendor_payment_applications"

    vendor_payment_id: Mapped[str] = mapped_column(
        db.ForeignKey("vendor_payments.id"), nullable=False, index=True
    )
    bill_id: Mapped[str] = mapped_column(
        db.ForeignKey("bills.id"), nullable=False, index=True
    )
    amount_applied: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False)

    bill = relationship("Bill", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "vendor_payment_id": self.vendor_payment_id,
            "bill_id": self.bill_id,
            "bill_number": self.bill.bill_number if self.bill else None,
            "amount_applied": str(self.amount_applied),
        }
