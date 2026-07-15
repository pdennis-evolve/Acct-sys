from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

ITEM_TYPES = ["inventory", "non_inventory", "service"]


class Item(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """SKU/catalog entry. Only item_type == 'inventory' carries stock
    levels and moves through receiving/sale transactions -- non_inventory
    and service items can still appear on invoices/bills/POs, they just
    never touch StockLevel."""

    __tablename__ = "items"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "sku", name="uq_items_tenant_sku"),
    )

    sku: Mapped[str] = mapped_column(db.String(50), nullable=False)
    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    item_type: Mapped[str] = mapped_column(db.String(20), nullable=False, default="inventory")

    unit_cost: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(14, 4), nullable=False, default=0)

    reorder_point: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    reorder_quantity: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    income_account_id: Mapped[str | None] = mapped_column(db.ForeignKey("accounts.id"), nullable=True)
    expense_account_id: Mapped[str | None] = mapped_column(db.ForeignKey("accounts.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    @property
    def tracks_inventory(self) -> bool:
        return self.item_type == "inventory"

    def to_dict(self, stock_summary=None):
        d = {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type,
            "unit_cost": str(self.unit_cost),
            "unit_price": str(self.unit_price),
            "reorder_point": self.reorder_point,
            "reorder_quantity": self.reorder_quantity,
            "income_account_id": self.income_account_id,
            "expense_account_id": self.expense_account_id,
            "is_active": self.is_active,
            "tracks_inventory": self.tracks_inventory,
        }
        if stock_summary is not None:
            d["quantity_on_hand"] = str(stock_summary.get("quantity_on_hand", Decimal("0")))
            d["below_reorder_point"] = stock_summary.get("below_reorder_point", False)
        return d
