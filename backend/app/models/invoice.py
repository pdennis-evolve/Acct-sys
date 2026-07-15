from decimal import Decimal

from datetime import date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

INVOICE_STATUSES = ["draft", "sent", "partial", "paid", "void"]


class Invoice(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    __tablename__ = "invoices"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "invoice_number", name="uq_invoices_tenant_number"),
    )

    customer_id: Mapped[str] = mapped_column(
        db.ForeignKey("customers.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    issue_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    due_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    tax_total: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    balance_due: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)

    memo: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(db.String(200), nullable=True)

    customer = relationship("Customer", lazy="joined")
    lines = relationship(
        "InvoiceLine", backref="invoice", cascade="all, delete-orphan",
        order_by="InvoiceLine.sort_order", lazy="selectin",
    )
    def recalculate_totals(self, tax_rate: Decimal = Decimal("0")):
        """Full recompute from line items + tax rate. Used on invoice
        create/edit, while the invoice is still in draft."""
        self.subtotal = sum((l.amount for l in self.lines), Decimal("0"))
        self.tax_total = (self.subtotal * tax_rate).quantize(Decimal("0.01"))
        self.total = self.subtotal + self.tax_total
        self.refresh_balance()

    def refresh_balance(self):
        """Recompute balance_due/status from existing total + applied
        payments, without touching subtotal/tax/total. Used whenever a
        payment is applied or unapplied.

        Queries PaymentApplication directly rather than through the
        `payment_applications` relationship: that relationship is
        selectin-loaded (eager, cached on first touch), so it goes stale
        the moment a sibling application is inserted later in the same
        session -- a direct aggregate always sees the latest flushed rows.
        """
        from sqlalchemy import func

        from app.models.payment import PaymentApplication

        applied = db.session.query(func.coalesce(func.sum(PaymentApplication.amount_applied), 0)).filter(
            PaymentApplication.invoice_id == self.id
        ).scalar()
        applied = Decimal(applied)
        self.balance_due = self.total - applied
        if self.status not in ("draft", "void"):
            if self.balance_due <= 0:
                self.status = "paid"
            elif applied > 0:
                self.status = "partial"

    def to_dict(self, include_lines=True):
        d = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.display_name if self.customer else None,
            "invoice_number": self.invoice_number,
            "status": self.status,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtotal": str(self.subtotal),
            "tax_total": str(self.tax_total),
            "total": str(self.total),
            "balance_due": str(self.balance_due),
            "memo": self.memo,
            "terms": self.terms,
        }
        if include_lines:
            d["lines"] = [l.to_dict() for l in self.lines]
        return d


class InvoiceLine(UUIDPKMixin, TenantScopedMixin, db.Model):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[str] = mapped_column(
        db.ForeignKey("invoices.id"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("accounts.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(db.String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "sort_order": self.sort_order,
        }
