from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin

INVENTORY_TXN_TYPES = ["receipt", "sale", "adjustment", "return"]


class StockLevel(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """Current on-hand quantity for one item at one location. Derived
    data -- always rebuilt by summing InventoryTransaction, never edited
    directly, so the ledger and the balance can never drift apart."""

    __tablename__ = "stock_levels"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "item_id", "location_id", name="uq_stock_levels_item_location"),
    )

    item_id: Mapped[str] = mapped_column(db.ForeignKey("items.id"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(db.ForeignKey("locations.id"), nullable=False, index=True)
    quantity_on_hand: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "quantity_on_hand": str(self.quantity_on_hand),
        }


class InventoryTransaction(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """Append-only stock movement ledger. StockLevel.quantity_on_hand is
    always the sum of quantity_delta for a given (item, location) --
    this table is the source of truth, never edited or deleted."""

    __tablename__ = "inventory_transactions"

    item_id: Mapped[str] = mapped_column(db.ForeignKey("items.id"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(db.ForeignKey("locations.id"), nullable=False, index=True)
    txn_type: Mapped[str] = mapped_column(db.String(20), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)
    txn_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    memo: Mapped[str | None] = mapped_column(db.String(500), nullable=True)

    reference_type: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(db.String(36), nullable=True)

    created_by: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "txn_type": self.txn_type,
            "quantity_delta": str(self.quantity_delta),
            "unit_cost": str(self.unit_cost),
            "txn_date": self.txn_date.isoformat() if self.txn_date else None,
            "memo": self.memo,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
