from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

WORK_ORDER_STATUSES = ["draft", "scheduled", "in_progress", "completed", "invoiced", "cancelled"]
WORK_ORDER_LINE_TYPES = ["labor", "part"]


class WorkOrder(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Job/ticket for a customer, assignable to a technician. Completing
    one decrements stock for any part line (mirrors invoice send) --
    converting to an invoice afterward never re-touches stock, it just
    bills for what already left the shelf."""

    __tablename__ = "work_orders"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "wo_number", name="uq_work_orders_tenant_number"),
    )

    customer_id: Mapped[str] = mapped_column(db.ForeignKey("customers.id"), nullable=False, index=True)
    wo_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    assigned_to: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)
    location_id: Mapped[str | None] = mapped_column(db.ForeignKey("locations.id"), nullable=True)

    problem_description: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    memo: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    scheduled_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    converted_invoice_id: Mapped[str | None] = mapped_column(db.ForeignKey("invoices.id"), nullable=True)

    customer = relationship("Customer", lazy="joined")
    technician = relationship("User", lazy="joined", foreign_keys=[assigned_to])
    lines = relationship(
        "WorkOrderLine", backref="work_order", cascade="all, delete-orphan",
        order_by="WorkOrderLine.sort_order", lazy="selectin",
    )

    def recalculate_totals(self):
        self.subtotal = sum((l.amount for l in self.lines), Decimal("0"))

    def to_dict(self, include_lines=True):
        d = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.display_name if self.customer else None,
            "wo_number": self.wo_number,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "technician_name": self.technician.full_name if self.technician else None,
            "location_id": self.location_id,
            "problem_description": self.problem_description,
            "memo": self.memo,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "subtotal": str(self.subtotal),
            "converted_invoice_id": self.converted_invoice_id,
        }
        if include_lines:
            d["lines"] = [l.to_dict() for l in self.lines]
        return d


class WorkOrderLine(UUIDPKMixin, TenantScopedMixin, db.Model):
    __tablename__ = "work_order_lines"

    work_order_id: Mapped[str] = mapped_column(db.ForeignKey("work_orders.id"), nullable=False, index=True)
    line_type: Mapped[str] = mapped_column(db.String(10), nullable=False, default="labor")
    item_id: Mapped[str | None] = mapped_column(db.ForeignKey("items.id"), nullable=True)
    account_id: Mapped[str | None] = mapped_column(db.ForeignKey("accounts.id"), nullable=True)
    description: Mapped[str] = mapped_column(db.String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "line_type": self.line_type,
            "item_id": self.item_id,
            "account_id": self.account_id,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "sort_order": self.sort_order,
        }
