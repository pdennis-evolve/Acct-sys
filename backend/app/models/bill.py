from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

BILL_STATUSES = ["draft", "pending_approval", "approved", "partial", "paid", "void"]


class Bill(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Vendor bill. Approval gate: draft -> pending_approval -> approved,
    only approved bills can be paid -- mirrors a real AP approval workflow
    rather than letting anyone with write access pay anything on sight."""

    __tablename__ = "bills"

    vendor_id: Mapped[str] = mapped_column(
        db.ForeignKey("vendors.id"), nullable=False, index=True
    )
    bill_number: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    bill_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    due_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    tax_total: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    balance_due: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)

    memo: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(db.String(200), nullable=True)

    approved_by: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True), nullable=True)

    vendor = relationship("Vendor", lazy="joined")
    lines = relationship(
        "BillLine", backref="bill", cascade="all, delete-orphan",
        order_by="BillLine.sort_order", lazy="selectin",
    )

    def recalculate_totals(self, tax_rate: Decimal = Decimal("0")):
        self.subtotal = sum((l.amount for l in self.lines), Decimal("0"))
        self.tax_total = (self.subtotal * tax_rate).quantize(Decimal("0.01"))
        self.total = self.subtotal + self.tax_total
        self.refresh_balance()

    def refresh_balance(self):
        from sqlalchemy import func

        from app.models.vendor_payment import VendorPaymentApplication

        applied = db.session.query(
            func.coalesce(func.sum(VendorPaymentApplication.amount_applied), 0)
        ).filter(VendorPaymentApplication.bill_id == self.id).scalar()
        applied = Decimal(applied)
        self.balance_due = self.total - applied
        if self.status not in ("draft", "pending_approval", "void"):
            if self.balance_due <= 0:
                self.status = "paid"
            elif applied > 0:
                self.status = "partial"

    def to_dict(self, include_lines=True):
        d = {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor.display_name if self.vendor else None,
            "bill_number": self.bill_number,
            "status": self.status,
            "bill_date": self.bill_date.isoformat() if self.bill_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtotal": str(self.subtotal),
            "tax_total": str(self.tax_total),
            "total": str(self.total),
            "balance_due": str(self.balance_due),
            "memo": self.memo,
            "terms": self.terms,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }
        if include_lines:
            d["lines"] = [l.to_dict() for l in self.lines]
        return d


class BillLine(UUIDPKMixin, TenantScopedMixin, db.Model):
    __tablename__ = "bill_lines"

    bill_id: Mapped[str] = mapped_column(
        db.ForeignKey("bills.id"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("accounts.id"), nullable=True
    )
    item_id: Mapped[str | None] = mapped_column(db.ForeignKey("items.id"), nullable=True)
    description: Mapped[str] = mapped_column(db.String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "item_id": self.item_id,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "sort_order": self.sort_order,
        }
