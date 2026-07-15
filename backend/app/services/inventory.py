from datetime import date
from decimal import Decimal

from flask import g

from app.extensions import db
from app.models.inventory import StockLevel, InventoryTransaction
from app.models.location import Location


def resolve_location(explicit_location_id):
    """Explicit location wins; otherwise fall back to the tenant's default.
    Returns None if neither exists (only matters for lines tied to an
    inventory-tracked item -- callers decide whether that's fatal)."""
    if explicit_location_id:
        loc = Location.query.filter_by(tenant_id=g.tenant_id, id=explicit_location_id).first()
        if loc:
            return loc
    return Location.query.filter_by(tenant_id=g.tenant_id, is_default=True).first()


def record_movement(item_id, location_id, txn_type, quantity_delta, unit_cost=None,
                     txn_date=None, memo=None, reference_type=None, reference_id=None):
    """Writes an InventoryTransaction and updates the matching StockLevel
    in lockstep. The transaction row is the source of truth; StockLevel
    is just a running total kept in sync here so reads don't have to
    re-sum the ledger every time.

    Caller must be inside a tenant-scoped request (relies on flask.g) and
    is responsible for committing alongside its own business record.
    """
    txn = InventoryTransaction(
        tenant_id=g.tenant_id,
        item_id=item_id,
        location_id=location_id,
        txn_type=txn_type,
        quantity_delta=quantity_delta,
        unit_cost=unit_cost if unit_cost is not None else Decimal("0"),
        txn_date=txn_date or date.today(),
        memo=memo,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=g.get("user_id"),
    )
    db.session.add(txn)

    stock = StockLevel.query.filter_by(
        tenant_id=g.tenant_id, item_id=item_id, location_id=location_id
    ).first()
    if not stock:
        stock = StockLevel(
            tenant_id=g.tenant_id, item_id=item_id, location_id=location_id,
            quantity_on_hand=Decimal("0"),
        )
        db.session.add(stock)
        db.session.flush()

    stock.quantity_on_hand = stock.quantity_on_hand + quantity_delta
    return txn, stock
