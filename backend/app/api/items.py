from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from app.extensions import db
from app.models import Item, ITEM_TYPES, StockLevel, InventoryTransaction, Location
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.inventory import record_movement, resolve_location

bp = Blueprint("items", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "warehouse_inventory")


def _stock_summary_for(item_ids):
    """Total on-hand quantity per item, summed across all locations."""
    if not item_ids:
        return {}
    rows = (
        db.session.query(StockLevel.item_id, func.coalesce(func.sum(StockLevel.quantity_on_hand), 0))
        .filter(StockLevel.tenant_id == g.tenant_id, StockLevel.item_id.in_(item_ids))
        .group_by(StockLevel.item_id)
        .all()
    )
    return {item_id: Decimal(total) for item_id, total in rows}


@bp.get("")
@tenant_required
@module_required("inventory")
def list_items():
    q = scoped_query(Item)
    search = request.args.get("q")
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Item.name.ilike(like), Item.sku.ilike(like)))
    item_type = request.args.get("item_type")
    if item_type:
        q = q.filter_by(item_type=item_type)
    items = q.order_by(Item.sku.asc()).all()

    stock = _stock_summary_for([i.id for i in items if i.tracks_inventory])
    results = []
    for item in items:
        qty = stock.get(item.id, Decimal("0"))
        summary = {"quantity_on_hand": qty, "below_reorder_point": item.tracks_inventory and qty <= item.reorder_point}
        results.append(item.to_dict(stock_summary=summary if item.tracks_inventory else None))

    if request.args.get("low_stock") == "true":
        results = [r for r in results if r.get("below_reorder_point")]

    return jsonify(items=results)


@bp.get("/<item_id>")
@tenant_required
@module_required("inventory")
def get_item(item_id):
    item = scoped_query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify(error="Item not found"), 404

    stock_by_location = []
    if item.tracks_inventory:
        levels = scoped_query(StockLevel).filter_by(item_id=item.id).all()
        locations = {l.id: l.name for l in scoped_query(Location).all()}
        stock_by_location = [
            {"location_id": lvl.location_id, "location_name": locations.get(lvl.location_id, "Unknown"), "quantity_on_hand": str(lvl.quantity_on_hand)}
            for lvl in levels
        ]

    total_qty = sum((Decimal(l["quantity_on_hand"]) for l in stock_by_location), Decimal("0"))
    summary = {"quantity_on_hand": total_qty, "below_reorder_point": item.tracks_inventory and total_qty <= item.reorder_point}
    d = item.to_dict(stock_summary=summary if item.tracks_inventory else None)
    d["stock_by_location"] = stock_by_location
    return jsonify(item=d)


@bp.get("/<item_id>/ledger")
@tenant_required
@module_required("inventory")
def item_ledger(item_id):
    item = scoped_query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify(error="Item not found"), 404
    txns = scoped_query(InventoryTransaction).filter_by(item_id=item.id).order_by(
        InventoryTransaction.txn_date.desc(), InventoryTransaction.created_at.desc()
    ).limit(200).all()
    return jsonify(transactions=[t.to_dict() for t in txns])


@bp.post("")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def create_item():
    data = request.get_json(silent=True) or {}
    sku = (data.get("sku") or "").strip()
    name = (data.get("name") or "").strip()
    item_type = data.get("item_type") or "inventory"
    if not sku or not name or item_type not in ITEM_TYPES:
        return jsonify(error="sku, name, and a valid item_type are required"), 400

    if scoped_query(Item).filter_by(sku=sku).first():
        return jsonify(error="An item with that SKU already exists"), 409

    try:
        unit_cost = Decimal(str(data.get("unit_cost", 0)))
        unit_price = Decimal(str(data.get("unit_price", 0)))
    except InvalidOperation:
        return jsonify(error="unit_cost and unit_price must be numeric"), 400

    item = stamp_tenant(Item(
        sku=sku, name=name, description=data.get("description"), item_type=item_type,
        unit_cost=unit_cost, unit_price=unit_price,
        reorder_point=int(data.get("reorder_point") or 0),
        reorder_quantity=int(data.get("reorder_quantity") or 0),
        income_account_id=data.get("income_account_id") or None,
        expense_account_id=data.get("expense_account_id") or None,
        created_by=g.user_id,
    ))
    db.session.add(item)
    db.session.flush()

    opening_qty = data.get("opening_quantity")
    if item.tracks_inventory and opening_qty:
        try:
            qty = Decimal(str(opening_qty))
        except InvalidOperation:
            qty = Decimal("0")
        if qty != 0:
            location = resolve_location(data.get("location_id"))
            if location:
                record_movement(
                    item_id=item.id, location_id=location.id, txn_type="adjustment",
                    quantity_delta=qty, unit_cost=unit_cost, txn_date=datetime.utcnow().date(),
                    memo="Opening balance", reference_type="opening_balance", reference_id=item.id,
                )

    log_action("item", item.id, "create", {"sku": sku, "name": name})
    db.session.commit()
    return jsonify(item=item.to_dict()), 201


@bp.patch("/<item_id>")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def update_item(item_id):
    item = scoped_query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify(error="Item not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("name", "description", "is_active"):
        if field in data:
            setattr(item, field, data[field])
            changes[field] = data[field]
    for field in ("income_account_id", "expense_account_id"):
        if field in data:
            setattr(item, field, data[field] or None)
    for field in ("reorder_point", "reorder_quantity"):
        if field in data:
            setattr(item, field, int(data[field] or 0))
    for field in ("unit_cost", "unit_price"):
        if field in data:
            try:
                setattr(item, field, Decimal(str(data[field])))
            except InvalidOperation:
                return jsonify(error=f"{field} must be numeric"), 400

    item.updated_by = g.user_id
    log_action("item", item.id, "update", changes)
    db.session.commit()
    return jsonify(item=item.to_dict())


@bp.delete("/<item_id>")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def delete_item(item_id):
    item = scoped_query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify(error="Item not found"), 404
    item.soft_delete(user_id=g.user_id)
    log_action("item", item.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")


@bp.post("/<item_id>/adjust")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def adjust_stock(item_id):
    """Manual stock correction (cycle count, damage, etc). Records the
    delta as its own ledger entry rather than editing StockLevel directly,
    so the adjustment itself is auditable."""
    item = scoped_query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify(error="Item not found"), 404
    if not item.tracks_inventory:
        return jsonify(error="This item does not track inventory"), 400

    data = request.get_json(silent=True) or {}
    try:
        delta = Decimal(str(data.get("quantity_delta", 0)))
    except InvalidOperation:
        return jsonify(error="quantity_delta must be numeric"), 400
    if delta == 0:
        return jsonify(error="quantity_delta must be non-zero"), 400

    location = resolve_location(data.get("location_id"))
    if not location:
        return jsonify(error="A location_id is required (and no default location exists for this tenant)"), 400

    txn, stock = record_movement(
        item_id=item.id, location_id=location.id, txn_type="adjustment",
        quantity_delta=delta, unit_cost=item.unit_cost,
        txn_date=datetime.utcnow().date(), memo=data.get("memo"),
        reference_type="manual_adjustment", reference_id=None,
    )
    log_action("item", item.id, "adjust", {"quantity_delta": str(delta), "location_id": location.id})
    db.session.commit()
    return jsonify(transaction=txn.to_dict(), stock_level=stock.to_dict()), 201
