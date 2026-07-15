from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import PurchaseOrder, PurchaseOrderLine, Vendor, Bill, BillLine, Item
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.inventory import record_movement, resolve_location

bp = Blueprint("purchase_orders", __name__)

WRITE_ROLES = ("owner_admin", "accountant")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _apply_lines(po, lines_data):
    po.lines.clear()
    for i, line in enumerate(lines_data or []):
        try:
            qty = Decimal(str(line.get("quantity", 1)))
            price = Decimal(str(line.get("unit_price", 0)))
        except InvalidOperation:
            continue
        amount = (qty * price).quantize(Decimal("0.01"))
        po.lines.append(PurchaseOrderLine(
            tenant_id=g.tenant_id,
            description=line.get("description", ""),
            quantity=qty,
            unit_price=price,
            amount=amount,
            account_id=line.get("account_id") or None,
            item_id=line.get("item_id") or None,
            sort_order=i,
        ))




def _next_po_number():
    last = scoped_query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).first()
    if not last:
        return "PO-1001"
    try:
        n = int(last.po_number.split("-")[-1]) + 1
    except (ValueError, IndexError):
        n = 1001
    return f"PO-{n}"


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_purchase_orders():
    q = scoped_query(PurchaseOrder)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    vendor_id = request.args.get("vendor_id")
    if vendor_id:
        q = q.filter_by(vendor_id=vendor_id)
    pos = q.order_by(PurchaseOrder.order_date.desc()).all()
    return jsonify(purchase_orders=[p.to_dict(include_lines=False) for p in pos])


@bp.get("/<po_id>")
@tenant_required
@module_required("ar_ap")
def get_purchase_order(po_id):
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    return jsonify(purchase_order=po.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_purchase_order():
    data = request.get_json(silent=True) or {}
    vendor_id = data.get("vendor_id")
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first() if vendor_id else None
    if not vendor:
        return jsonify(error="A valid vendor_id is required"), 400

    po = stamp_tenant(PurchaseOrder(
        vendor_id=vendor.id,
        po_number=data.get("po_number") or _next_po_number(),
        status="draft",
        order_date=_parse_date(data.get("order_date"), datetime.utcnow().date()),
        expected_date=_parse_date(data.get("expected_date")),
        memo=data.get("memo"),
        location_id=data.get("location_id") or None,
        created_by=g.user_id,
    ))
    _apply_lines(po, data.get("lines"))
    po.recalculate_totals()

    db.session.add(po)
    db.session.flush()
    log_action("purchase_order", po.id, "create", {"po_number": po.po_number})
    db.session.commit()
    return jsonify(purchase_order=po.to_dict()), 201


@bp.patch("/<po_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_purchase_order(po_id):
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    if po.status != "draft":
        return jsonify(error=f"Purchase order in status '{po.status}' cannot be edited"), 409

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("memo",):
        if field in data:
            setattr(po, field, data[field])
            changes[field] = data[field]
    if "order_date" in data:
        po.order_date = _parse_date(data["order_date"])
    if "expected_date" in data:
        po.expected_date = _parse_date(data["expected_date"])
    if "location_id" in data:
        po.location_id = data["location_id"] or None
    if "lines" in data:
        _apply_lines(po, data["lines"])
        changes["lines"] = "updated"

    po.recalculate_totals()
    po.updated_by = g.user_id
    log_action("purchase_order", po.id, "update", changes)
    db.session.commit()
    return jsonify(purchase_order=po.to_dict())


@bp.post("/<po_id>/send")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def send_purchase_order(po_id):
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    if po.status != "draft":
        return jsonify(error=f"Purchase order in status '{po.status}' cannot be sent"), 409
    po.status = "sent"
    po.updated_by = g.user_id
    log_action("purchase_order", po.id, "send")
    db.session.commit()
    return jsonify(purchase_order=po.to_dict())


@bp.post("/<po_id>/receive")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def receive_purchase_order(po_id):
    """Marks goods received and increments stock for any line tied to an
    inventory-tracked Item, at the PO's location (or the tenant default)."""
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    if po.status != "sent":
        return jsonify(error=f"Purchase order in status '{po.status}' cannot be received"), 409

    item_ids = [l.item_id for l in po.lines if l.item_id]
    if item_ids:
        items = {i.id: i for i in scoped_query(Item).filter(Item.id.in_(item_ids)).all()}
        inventory_lines = [l for l in po.lines if l.item_id and items.get(l.item_id) and items[l.item_id].tracks_inventory]
        if inventory_lines:
            location = resolve_location(po.location_id)
            if not location:
                return jsonify(error="No location set on this PO and no default location exists for this tenant"), 400
            for line in inventory_lines:
                record_movement(
                    item_id=line.item_id, location_id=location.id, txn_type="receipt",
                    quantity_delta=line.quantity, unit_cost=line.unit_price,
                    txn_date=datetime.utcnow().date(), memo=f"Received via {po.po_number}",
                    reference_type="purchase_order", reference_id=po.id,
                )

    po.status = "received"
    po.updated_by = g.user_id
    log_action("purchase_order", po.id, "receive")
    db.session.commit()
    return jsonify(purchase_order=po.to_dict())


@bp.post("/<po_id>/cancel")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def cancel_purchase_order(po_id):
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    if po.status in ("closed", "cancelled"):
        return jsonify(error=f"Purchase order already {po.status}"), 409
    po.status = "cancelled"
    po.updated_by = g.user_id
    log_action("purchase_order", po.id, "cancel")
    db.session.commit()
    return jsonify(purchase_order=po.to_dict())


@bp.post("/<po_id>/convert-to-bill")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def convert_to_bill(po_id):
    """Creates a draft Bill pre-filled from this PO's lines, and closes
    the PO. The bill still goes through its own submit/approve workflow."""
    po = scoped_query(PurchaseOrder).filter_by(id=po_id).first()
    if not po:
        return jsonify(error="Purchase order not found"), 404
    if po.status not in ("sent", "received"):
        return jsonify(error=f"Purchase order in status '{po.status}' cannot be converted to a bill"), 409
    if po.converted_bill_id:
        return jsonify(error="Purchase order already converted to a bill"), 409

    today = datetime.utcnow().date()
    bill = stamp_tenant(Bill(
        vendor_id=po.vendor_id,
        status="draft",
        bill_date=today,
        due_date=today + timedelta(days=30),
        memo=f"Generated from {po.po_number}",
        created_by=g.user_id,
    ))
    for line in po.lines:
        bill.lines.append(BillLine(
            tenant_id=g.tenant_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            amount=line.amount,
            account_id=line.account_id,
            item_id=line.item_id,
            sort_order=line.sort_order,
        ))
    bill.recalculate_totals()
    db.session.add(bill)
    db.session.flush()

    po.converted_bill_id = bill.id
    po.status = "closed"
    po.updated_by = g.user_id

    log_action("purchase_order", po.id, "convert_to_bill", {"bill_id": bill.id})
    db.session.commit()
    return jsonify(purchase_order=po.to_dict(), bill=bill.to_dict()), 201
