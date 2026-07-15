from decimal import Decimal

from datetime import date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

PAYMENT_METHODS = ["cash", "check", "credit_card", "ach", "other"]


class Payment(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Customer receipt: money received, applied across one or more invoices."""

    __tablename__ = "payments"

    customer_id: Mapped[str] = mapped_column(
        db.ForeignKey("customers.id"), nullable=False, index=True
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
        "PaymentApplication", backref="payment", cascade="all, delete-orphan", lazy="selectin"
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
            "customer_id": self.customer_id,
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


class PaymentApplication(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "payment_applications"

    payment_id: Mapped[str] = mapped_column(
        db.ForeignKey("payments.id"), nullable=False, index=True
    )
    invoice_id: Mapped[str] = mapped_column(
        db.ForeignKey("invoices.id"), nullable=False, index=True
    )
    amount_applied: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False)

    invoice = relationship("Invoice", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice.invoice_number if self.invoice else None,
            "amount_applied": str(self.amount_applied),
        }
