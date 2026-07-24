from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import WorkOrder, WorkOrderLine, Customer, User, Item, Invoice, InvoiceLine, CompanySettings
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.inventory import record_movement, resolve_location

bp = Blueprint("work_orders", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "dispatcher")


def _can_manage(wo):
    """Dispatcher/accountant/owner can manage any work order; a technician
    can only touch the ones assigned to them -- mirrors a real crew
    workflow where techs work their own tickets, not everyone else's."""
    if g.role in WRITE_ROLES:
        return True
    return g.role == "technician" and wo.assigned_to == g.user_id


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _apply_lines(wo, lines_data):
    wo.lines.clear()
    for i, line in enumerate(lines_data or []):
        try:
            qty = Decimal(str(line.get("quantity", 1)))
            price = Decimal(str(line.get("unit_price", 0)))
        except InvalidOperation:
            continue
        line_type = line.get("line_type") if line.get("line_type") in ("labor", "part") else "labor"
        amount = (qty * price).quantize(Decimal("0.01"))
        wo.lines.append(WorkOrderLine(
            tenant_id=g.tenant_id,
            line_type=line_type,
            item_id=line.get("item_id") or None if line_type == "part" else None,
            account_id=line.get("account_id") or None,
            description=line.get("description", ""),
            quantity=qty,
            unit_price=price,
            amount=amount,
            sort_order=i,
        ))


def _next_wo_number():
    last = scoped_query(WorkOrder).order_by(WorkOrder.created_at.desc()).first()
    if not last:
        return "WO-1001"
    try:
        n = int(last.wo_number.split("-")[-1]) + 1
    except (ValueError, IndexError):
        n = 1001
    return f"WO-{n}"


@bp.get("")
@tenant_required
@module_required("work_orders")
def list_work_orders():
    q = scoped_query(WorkOrder)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    assigned_to = request.args.get("assigned_to")
    if assigned_to:
        q = q.filter_by(assigned_to=assigned_to)
    project_id = request.args.get("project_id")
    if project_id:
        q = q.filter_by(project_id=project_id)
    if g.role == "technician" and request.args.get("mine") == "true":
        q = q.filter_by(assigned_to=g.user_id)
    wos = q.order_by(WorkOrder.created_at.desc()).all()
    return jsonify(work_orders=[w.to_dict(include_lines=False) for w in wos])


@bp.get("/technicians")
@tenant_required
@module_required("work_orders")
@role_required(*WRITE_ROLES)
def list_technicians():
    """Lightweight roster for the assignment dropdown -- dispatchers need
    this but shouldn't get the full user list (that's owner_admin-only)."""
    techs = scoped_query(User).filter_by(role="technician", is_active=True).order_by(User.full_name.asc()).all()
    return jsonify(technicians=[{"id": t.id, "full_name": t.full_name} for t in techs])


@bp.get("/<wo_id>")
@tenant_required
@module_required("work_orders")
def get_work_order(wo_id):
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    return jsonify(work_order=wo.to_dict())


@bp.post("")
@tenant_required
@module_required("work_orders")
@role_required(*WRITE_ROLES)
def create_work_order():
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    customer = scoped_query(Customer).filter_by(id=customer_id).first() if customer_id else None
    if not customer:
        return jsonify(error="A valid customer_id is required"), 400

    assigned_to = data.get("assigned_to") or None
    if assigned_to and not scoped_query(User).filter_by(id=assigned_to, role="technician").first():
        return jsonify(error="assigned_to must be a technician in this tenant"), 400

    wo = stamp_tenant(WorkOrder(
        customer_id=customer.id,
        wo_number=data.get("wo_number") or _next_wo_number(),
        status="draft",
        assigned_to=assigned_to,
        location_id=data.get("location_id") or None,
        project_id=data.get("project_id") or None,
        problem_description=data.get("problem_description"),
        memo=data.get("memo"),
        scheduled_date=_parse_date(data.get("scheduled_date")),
        created_by=g.user_id,
    ))
    _apply_lines(wo, data.get("lines"))
    wo.recalculate_totals()

    db.session.add(wo)
    db.session.flush()
    log_action("work_order", wo.id, "create", {"wo_number": wo.wo_number})
    db.session.commit()
    return jsonify(work_order=wo.to_dict()), 201


@bp.patch("/<wo_id>")
@tenant_required
@module_required("work_orders")
def update_work_order(wo_id):
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if not _can_manage(wo):
        return jsonify(error="You are not assigned to this work order"), 403
    if wo.status not in ("draft", "scheduled", "in_progress"):
        return jsonify(error=f"Work order in status '{wo.status}' cannot be edited"), 409

    data = request.get_json(silent=True) or {}
    changes = {}
    if "problem_description" in data:
        wo.problem_description = data["problem_description"]
        changes["problem_description"] = data["problem_description"]
    if "memo" in data:
        wo.memo = data["memo"]
    if "scheduled_date" in data:
        wo.scheduled_date = _parse_date(data["scheduled_date"])
    if "assigned_to" in data:
        assigned_to = data["assigned_to"] or None
        if assigned_to and not scoped_query(User).filter_by(id=assigned_to, role="technician").first():
            return jsonify(error="assigned_to must be a technician in this tenant"), 400
        wo.assigned_to = assigned_to
    if "location_id" in data:
        wo.location_id = data["location_id"] or None
    if "project_id" in data:
        wo.project_id = data["project_id"] or None
    if "lines" in data:
        _apply_lines(wo, data["lines"])
        changes["lines"] = "updated"

    wo.recalculate_totals()
    wo.updated_by = g.user_id
    log_action("work_order", wo.id, "update", changes)
    db.session.commit()
    return jsonify(work_order=wo.to_dict())


@bp.post("/<wo_id>/schedule")
@tenant_required
@module_required("work_orders")
@role_required(*WRITE_ROLES)
def schedule_work_order(wo_id):
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if wo.status != "draft":
        return jsonify(error=f"Work order in status '{wo.status}' cannot be scheduled"), 409

    data = request.get_json(silent=True) or {}
    scheduled_date = _parse_date(data.get("scheduled_date"), wo.scheduled_date)
    if not scheduled_date:
        return jsonify(error="scheduled_date is required"), 400
    assigned_to = data.get("assigned_to", wo.assigned_to)
    if assigned_to and not scoped_query(User).filter_by(id=assigned_to, role="technician").first():
        return jsonify(error="assigned_to must be a technician in this tenant"), 400

    wo.scheduled_date = scheduled_date
    wo.assigned_to = assigned_to
    wo.status = "scheduled"
    wo.updated_by = g.user_id
    log_action("work_order", wo.id, "schedule")
    db.session.commit()
    return jsonify(work_order=wo.to_dict())


@bp.post("/<wo_id>/start")
@tenant_required
@module_required("work_orders")
def start_work_order(wo_id):
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if not _can_manage(wo):
        return jsonify(error="You are not assigned to this work order"), 403
    if wo.status != "scheduled":
        return jsonify(error=f"Work order in status '{wo.status}' cannot be started"), 409
    wo.status = "in_progress"
    wo.updated_by = g.user_id
    log_action("work_order", wo.id, "start")
    db.session.commit()
    return jsonify(work_order=wo.to_dict())


@bp.post("/<wo_id>/complete")
@tenant_required
@module_required("work_orders")
def complete_work_order(wo_id):
    """in_progress -> completed. Decrements stock for any part line, the
    same as an invoice send -- this is the point where parts actually
    leave inventory, well before (or even without) an invoice existing."""
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if not _can_manage(wo):
        return jsonify(error="You are not assigned to this work order"), 403
    if wo.status != "in_progress":
        return jsonify(error=f"Work order in status '{wo.status}' cannot be completed"), 409

    part_lines = [l for l in wo.lines if l.line_type == "part" and l.item_id]
    if part_lines:
        items = {i.id: i for i in scoped_query(Item).filter(Item.id.in_([l.item_id for l in part_lines])).all()}
        inventory_lines = [l for l in part_lines if items.get(l.item_id) and items[l.item_id].tracks_inventory]
        if inventory_lines:
            location = resolve_location(wo.location_id)
            if not location:
                return jsonify(error="No location set on this work order and no default location exists for this tenant"), 400
            for line in inventory_lines:
                record_movement(
                    item_id=line.item_id, location_id=location.id, txn_type="sale",
                    quantity_delta=-line.quantity, unit_cost=items[line.item_id].unit_cost,
                    txn_date=datetime.utcnow().date(), memo=f"Used on {wo.wo_number}",
                    reference_type="work_order", reference_id=wo.id,
                )

    wo.status = "completed"
    wo.completed_at = datetime.now(timezone.utc)
    wo.updated_by = g.user_id
    log_action("work_order", wo.id, "complete")
    db.session.commit()
    return jsonify(work_order=wo.to_dict())


@bp.post("/<wo_id>/cancel")
@tenant_required
@module_required("work_orders")
@role_required(*WRITE_ROLES)
def cancel_work_order(wo_id):
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if wo.status in ("completed", "invoiced", "cancelled"):
        return jsonify(error=f"Work order in status '{wo.status}' cannot be cancelled"), 409
    wo.status = "cancelled"
    wo.updated_by = g.user_id
    log_action("work_order", wo.id, "cancel")
    db.session.commit()
    return jsonify(work_order=wo.to_dict())


@bp.post("/<wo_id>/convert-to-invoice")
@tenant_required
@module_required("ar_ap")
@module_required("work_orders")
@role_required(*WRITE_ROLES)
def convert_to_invoice(wo_id):
    """Creates a draft Invoice pre-filled from this WO's lines. Line
    item_id is deliberately NOT carried over -- stock for parts already
    moved at completion, and sending this invoice must not decrement it
    a second time."""
    wo = scoped_query(WorkOrder).filter_by(id=wo_id).first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    if wo.status != "completed":
        return jsonify(error=f"Work order in status '{wo.status}' cannot be converted to an invoice"), 409
    if wo.converted_invoice_id:
        return jsonify(error="Work order already converted to an invoice"), 409
    if not wo.lines:
        return jsonify(error="Cannot convert a work order with no line items"), 400

    from app.api.invoices import _next_invoice_number

    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    terms_days = settings.default_invoice_terms_days if settings else 30
    today = datetime.utcnow().date()

    invoice = stamp_tenant(Invoice(
        customer_id=wo.customer_id,
        invoice_number=_next_invoice_number(),
        status="draft",
        issue_date=today,
        due_date=today + timedelta(days=terms_days),
        memo=f"Generated from {wo.wo_number}",
        created_by=g.user_id,
    ))
    for line in wo.lines:
        invoice.lines.append(InvoiceLine(
            tenant_id=g.tenant_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            amount=line.amount,
            account_id=line.account_id,
            sort_order=line.sort_order,
        ))
    invoice.recalculate_totals(Decimal("0"), None)
    db.session.add(invoice)
    db.session.flush()

    wo.converted_invoice_id = invoice.id
    wo.status = "invoiced"
    wo.updated_by = g.user_id

    log_action("work_order", wo.id, "convert_to_invoice", {"invoice_id": invoice.id})
    db.session.commit()
    return jsonify(work_order=wo.to_dict(), invoice=invoice.to_dict()), 201
