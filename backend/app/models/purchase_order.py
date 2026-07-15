from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

PO_STATUSES = ["draft", "sent", "received", "closed", "cancelled"]


class PurchaseOrder(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Tracked manually for now (draft/sent/received/closed/cancelled) --
    inventory stock wiring lands in Phase 3 alongside items/SKUs."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "po_number", name="uq_purchase_orders_tenant_number"),
    )

    vendor_id: Mapped[str] = mapped_column(
        db.ForeignKey("vendors.id"), nullable=False, index=True
    )
    po_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    memo: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    converted_bill_id: Mapped[str | None] = mapped_column(db.ForeignKey("bills.id"), nullable=True)

    vendor = relationship("Vendor", lazy="joined")
    lines = relationship(
        "PurchaseOrderLine", backref="purchase_order", cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.sort_order", lazy="selectin",
    )

    def recalculate_totals(self):
        self.subtotal = sum((l.amount for l in self.lines), Decimal("0"))

    def to_dict(self, include_lines=True):
        d = {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor.display_name if self.vendor else None,
            "po_number": self.po_number,
            "status": self.status,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "expected_date": self.expected_date.isoformat() if self.expected_date else None,
            "subtotal": str(self.subtotal),
            "memo": self.memo,
            "converted_bill_id": self.converted_bill_id,
        }
        if include_lines:
            d["lines"] = [l.to_dict() for l in self.lines]
        return d


class PurchaseOrderLine(UUIDPKMixin, TenantScopedMixin, db.Model):
    __tablename__ = "purchase_order_lines"

    purchase_order_id: Mapped[str] = mapped_column(
        db.ForeignKey("purchase_orders.id"), nullable=False, index=True
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
