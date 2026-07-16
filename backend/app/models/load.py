from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

LOAD_STATUSES = ["draft", "scheduled", "dispatched", "in_transit", "delivered", "invoiced", "cancelled"]


class Load(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Dispatch record: a shipment for a customer, assigned to a driver
    and vehicle. draft -> scheduled -> dispatched -> in_transit ->
    delivered -> invoiced, or cancelled before delivery."""

    __tablename__ = "loads"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "load_number", name="uq_loads_tenant_number"),
    )

    customer_id: Mapped[str] = mapped_column(db.ForeignKey("customers.id"), nullable=False, index=True)
    load_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    driver_id: Mapped[str | None] = mapped_column(db.ForeignKey("drivers.id"), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(db.ForeignKey("vehicles.id"), nullable=True)

    origin: Mapped[str | None] = mapped_column(db.String(300), nullable=True)
    destination: Mapped[str | None] = mapped_column(db.String(300), nullable=True)
    pickup_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)

    base_rate: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    memo: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    converted_invoice_id: Mapped[str | None] = mapped_column(db.ForeignKey("invoices.id"), nullable=True)

    customer = relationship("Customer", lazy="joined")
    driver = relationship("Driver", lazy="joined")
    vehicle = relationship("Vehicle", lazy="joined")
    charges = relationship(
        "LoadCharge", backref="load", cascade="all, delete-orphan",
        order_by="LoadCharge.sort_order", lazy="selectin",
    )

    def recalculate_totals(self):
        self.total = self.base_rate + sum((c.amount for c in self.charges), Decimal("0"))

    def to_dict(self, include_charges=True):
        d = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.display_name if self.customer else None,
            "load_number": self.load_number,
            "status": self.status,
            "driver_id": self.driver_id,
            "driver_name": self.driver.full_name if self.driver else None,
            "vehicle_id": self.vehicle_id,
            "vehicle_unit_number": self.vehicle.unit_number if self.vehicle else None,
            "origin": self.origin,
            "destination": self.destination,
            "pickup_date": self.pickup_date.isoformat() if self.pickup_date else None,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "base_rate": str(self.base_rate),
            "total": str(self.total),
            "memo": self.memo,
            "converted_invoice_id": self.converted_invoice_id,
        }
        if include_charges:
            d["charges"] = [c.to_dict() for c in self.charges]
        return d


class LoadCharge(UUIDPKMixin, TenantScopedMixin, db.Model):
    """Accessorial charges -- fuel surcharge, detention, lumper, etc."""

    __tablename__ = "load_charges"

    load_id: Mapped[str] = mapped_column(db.ForeignKey("loads.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(db.String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "amount": str(self.amount),
            "sort_order": self.sort_order,
        }
