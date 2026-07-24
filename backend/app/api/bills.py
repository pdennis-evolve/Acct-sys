from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Bill, BillLine, Vendor
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("bills", __name__)

WRITE_ROLES = ("owner_admin", "accountant")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _apply_lines(bill, lines_data):
    bill.lines.clear()
    for i, line in enumerate(lines_data or []):
        try:
            qty = Decimal(str(line.get("quantity", 1)))
            price = Decimal(str(line.get("unit_price", 0)))
        except InvalidOperation:
            continue
        amount = (qty * price).quantize(Decimal("0.01"))
        bill.lines.append(BillLine(
            tenant_id=g.tenant_id,
            description=line.get("description", ""),
            quantity=qty,
            unit_price=price,
            amount=amount,
            account_id=line.get("account_id") or None,
            item_id=line.get("item_id") or None,
            sort_order=i,
        ))


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_bills():
    q = scoped_query(Bill)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    vendor_id = request.args.get("vendor_id")
    if vendor_id:
        q = q.filter_by(vendor_id=vendor_id)
    project_id = request.args.get("project_id")
    if project_id:
        q = q.filter_by(project_id=project_id)
    bills = q.order_by(Bill.bill_date.desc()).all()
    return jsonify(bills=[b.to_dict(include_lines=False) for b in bills])


@bp.get("/<bill_id>")
@tenant_required
@module_required("ar_ap")
def get_bill(bill_id):
    bill = scoped_query(Bill).filter_by(id=bill_id).first()
    if not bill:
        return jsonify(error="Bill not found"), 404
    return jsonify(bill=bill.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_bill():
    data = request.get_json(silent=True) or {}
    vendor_id = data.get("vendor_id")
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first() if vendor_id else None
    if not vendor:
        return jsonify(error="A valid vendor_id is required"), 400

    bill_date = _parse_date(data.get("bill_date"), datetime.utcnow().date())
    due_date = _parse_date(data.get("due_date"), bill_date + timedelta(days=30))

    bill = stamp_tenant(Bill(
        vendor_id=vendor.id,
        bill_number=data.get("bill_number"),
        status="draft",
        bill_date=bill_date,
        due_date=due_date,
        memo=data.get("memo"),
        terms=data.get("terms"),
        project_id=data.get("project_id") or None,
        created_by=g.user_id,
    ))
    _apply_lines(bill, data.get("lines"))
    bill.recalculate_totals(Decimal(str(data.get("tax_rate", 0))))

    db.session.add(bill)
    db.session.flush()
    log_action("bill", bill.id, "create", {"bill_number": bill.bill_number, "total": str(bill.total)})
    db.session.commit()
    return jsonify(bill=bill.to_dict()), 201


@bp.patch("/<bill_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_bill(bill_id):
    bill = scoped_query(Bill).filter_by(id=bill_id).first()
    if not bill:
        return jsonify(error="Bill not found"), 404
    if bill.status != "draft":
        return jsonify(error=f"Bill in status '{bill.status}' cannot be edited"), 409

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("memo", "terms", "bill_number"):
        if field in data:
            setattr(bill, field, data[field])
            changes[field] = data[field]
    if "bill_date" in data:
        bill.bill_date = _parse_date(data["bill_date"])
    if "due_date" in data:
        bill.due_date = _parse_date(data["due_date"])
    if "project_id" in data:
        bill.project_id = data["project_id"] or None
    if "lines" in data:
        _apply_lines(bill, data["lines"])
        changes["lines"] = "updated"

    bill.recalculate_totals(Decimal(str(data.get("tax_rate", 0))))
    bill.updated_by = g.user_id
    log_action("bill", bill.id, "update", changes)
    db.session.commit()
    return jsonify(bill=bill.to_dict())


@bp.post("/<bill_id>/submit")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def submit_bill(bill_id):
    """draft -> pending_approval. Bill is now locked and awaits sign-off."""
    bill = scoped_query(Bill).filter_by(id=bill_id).first()
    if not bill:
        return jsonify(error="Bill not found"), 404
    if bill.status != "draft":
        return jsonify(error=f"Bill in status '{bill.status}' cannot be submitted"), 409
    if not bill.lines:
        return jsonify(error="Cannot submit a bill with no line items"), 400
    bill.status = "pending_approval"
    bill.updated_by = g.user_id
    log_action("bill", bill.id, "submit")
    db.session.commit()
    return jsonify(bill=bill.to_dict())


@bp.post("/<bill_id>/approve")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def approve_bill(bill_id):
    """pending_approval -> approved. Only approved bills can be paid."""
    bill = scoped_query(Bill).filter_by(id=bill_id).first()
    if not bill:
        return jsonify(error="Bill not found"), 404
    if bill.status != "pending_approval":
        return jsonify(error=f"Bill in status '{bill.status}' cannot be approved"), 409
    bill.status = "approved"
    bill.approved_by = g.user_id
    bill.approved_at = datetime.now(timezone.utc)
    bill.updated_by = g.user_id
    log_action("bill", bill.id, "approve")
    db.session.commit()
    return jsonify(bill=bill.to_dict())


@bp.post("/<bill_id>/void")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def void_bill(bill_id):
    bill = scoped_query(Bill).filter_by(id=bill_id).first()
    if not bill:
        return jsonify(error="Bill not found"), 404
    if bill.status in ("paid",):
        return jsonify(error="A paid bill cannot be voided"), 409
    bill.status = "void"
    bill.balance_due = Decimal("0")
    bill.updated_by = g.user_id
    log_action("bill", bill.id, "void")
    db.session.commit()
    return jsonify(bill=bill.to_dict())
