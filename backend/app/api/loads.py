from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Load, LoadCharge, Customer, Driver, Vehicle, Invoice, InvoiceLine, CompanySettings
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("loads", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "dispatcher")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _apply_charges(load, charges_data):
    load.charges.clear()
    for i, charge in enumerate(charges_data or []):
        try:
            amount = Decimal(str(charge.get("amount", 0)))
        except InvalidOperation:
            continue
        load.charges.append(LoadCharge(
            tenant_id=g.tenant_id,
            description=charge.get("description", ""),
            amount=amount,
            sort_order=i,
        ))


def _next_load_number():
    last = scoped_query(Load).order_by(Load.created_at.desc()).first()
    if not last:
        return "LD-1001"
    try:
        n = int(last.load_number.split("-")[-1]) + 1
    except (ValueError, IndexError):
        n = 1001
    return f"LD-{n}"


@bp.get("")
@tenant_required
@module_required("transportation")
def list_loads():
    q = scoped_query(Load)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    driver_id = request.args.get("driver_id")
    if driver_id:
        q = q.filter_by(driver_id=driver_id)
    loads = q.order_by(Load.created_at.desc()).all()
    return jsonify(loads=[l.to_dict(include_charges=False) for l in loads])


@bp.get("/<load_id>")
@tenant_required
@module_required("transportation")
def get_load(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    return jsonify(load=load.to_dict())


@bp.post("")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def create_load():
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    customer = scoped_query(Customer).filter_by(id=customer_id).first() if customer_id else None
    if not customer:
        return jsonify(error="A valid customer_id is required"), 400

    try:
        base_rate = Decimal(str(data.get("base_rate", 0)))
    except InvalidOperation:
        return jsonify(error="base_rate must be numeric"), 400

    load = stamp_tenant(Load(
        customer_id=customer.id,
        load_number=data.get("load_number") or _next_load_number(),
        status="draft",
        origin=data.get("origin"),
        destination=data.get("destination"),
        pickup_date=_parse_date(data.get("pickup_date")),
        base_rate=base_rate,
        memo=data.get("memo"),
        created_by=g.user_id,
    ))
    _apply_charges(load, data.get("charges"))
    load.recalculate_totals()

    db.session.add(load)
    db.session.flush()
    log_action("load", load.id, "create", {"load_number": load.load_number})
    db.session.commit()
    return jsonify(load=load.to_dict()), 201


@bp.patch("/<load_id>")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def update_load(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status not in ("draft", "scheduled"):
        return jsonify(error=f"Load in status '{load.status}' cannot be edited"), 409

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("origin", "destination", "memo"):
        if field in data:
            setattr(load, field, data[field])
            changes[field] = data[field]
    if "pickup_date" in data:
        load.pickup_date = _parse_date(data["pickup_date"])
    if "base_rate" in data:
        try:
            load.base_rate = Decimal(str(data["base_rate"]))
        except InvalidOperation:
            return jsonify(error="base_rate must be numeric"), 400
    if "charges" in data:
        _apply_charges(load, data["charges"])
        changes["charges"] = "updated"

    load.recalculate_totals()
    load.updated_by = g.user_id
    log_action("load", load.id, "update", changes)
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/schedule")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def schedule_load(load_id):
    """draft -> scheduled. Assigns the driver + vehicle for this run."""
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status != "draft":
        return jsonify(error=f"Load in status '{load.status}' cannot be scheduled"), 409

    data = request.get_json(silent=True) or {}
    driver_id = data.get("driver_id")
    vehicle_id = data.get("vehicle_id")
    if not driver_id or not vehicle_id:
        return jsonify(error="driver_id and vehicle_id are required to schedule a load"), 400
    if not scoped_query(Driver).filter_by(id=driver_id).first():
        return jsonify(error="driver_id not found"), 400
    if not scoped_query(Vehicle).filter_by(id=vehicle_id).first():
        return jsonify(error="vehicle_id not found"), 400

    load.driver_id = driver_id
    load.vehicle_id = vehicle_id
    if data.get("pickup_date"):
        load.pickup_date = _parse_date(data["pickup_date"])
    load.status = "scheduled"
    load.updated_by = g.user_id
    log_action("load", load.id, "schedule", {"driver_id": driver_id, "vehicle_id": vehicle_id})
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/dispatch")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def dispatch_load(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status != "scheduled":
        return jsonify(error=f"Load in status '{load.status}' cannot be dispatched"), 409
    load.status = "dispatched"
    load.updated_by = g.user_id
    log_action("load", load.id, "dispatch")
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/start-transit")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def start_transit(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status != "dispatched":
        return jsonify(error=f"Load in status '{load.status}' cannot start transit"), 409
    load.status = "in_transit"
    load.updated_by = g.user_id
    log_action("load", load.id, "start_transit")
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/deliver")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def deliver_load(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status != "in_transit":
        return jsonify(error=f"Load in status '{load.status}' cannot be marked delivered"), 409

    data = request.get_json(silent=True) or {}
    load.delivery_date = _parse_date(data.get("delivery_date"), datetime.utcnow().date())
    load.status = "delivered"
    load.updated_by = g.user_id
    log_action("load", load.id, "deliver")
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/cancel")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def cancel_load(load_id):
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status in ("delivered", "invoiced", "cancelled"):
        return jsonify(error=f"Load in status '{load.status}' cannot be cancelled"), 409
    load.status = "cancelled"
    load.updated_by = g.user_id
    log_action("load", load.id, "cancel")
    db.session.commit()
    return jsonify(load=load.to_dict())


@bp.post("/<load_id>/convert-to-invoice")
@tenant_required
@module_required("ar_ap")
@module_required("transportation")
@role_required(*WRITE_ROLES)
def convert_to_invoice(load_id):
    """Creates a draft Invoice from the base rate + accessorial charges."""
    load = scoped_query(Load).filter_by(id=load_id).first()
    if not load:
        return jsonify(error="Load not found"), 404
    if load.status != "delivered":
        return jsonify(error=f"Load in status '{load.status}' cannot be converted to an invoice"), 409
    if load.converted_invoice_id:
        return jsonify(error="Load already converted to an invoice"), 409

    from app.api.invoices import _next_invoice_number

    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    terms_days = settings.default_invoice_terms_days if settings else 30
    today = datetime.utcnow().date()

    invoice = stamp_tenant(Invoice(
        customer_id=load.customer_id,
        invoice_number=_next_invoice_number(),
        status="draft",
        issue_date=today,
        due_date=today + timedelta(days=terms_days),
        memo=f"Generated from {load.load_number}: {load.origin or ''} -> {load.destination or ''}".strip(),
        created_by=g.user_id,
    ))
    invoice.lines.append(InvoiceLine(
        tenant_id=g.tenant_id,
        description=f"Freight: {load.origin or 'origin'} to {load.destination or 'destination'} ({load.load_number})",
        quantity=Decimal("1"),
        unit_price=load.base_rate,
        amount=load.base_rate,
        sort_order=0,
    ))
    for i, charge in enumerate(load.charges):
        invoice.lines.append(InvoiceLine(
            tenant_id=g.tenant_id,
            description=charge.description,
            quantity=Decimal("1"),
            unit_price=charge.amount,
            amount=charge.amount,
            sort_order=i + 1,
        ))
    invoice.recalculate_totals(Decimal("0"), None)
    db.session.add(invoice)
    db.session.flush()

    load.converted_invoice_id = invoice.id
    load.status = "invoiced"
    load.updated_by = g.user_id

    log_action("load", load.id, "convert_to_invoice", {"invoice_id": invoice.id})
    db.session.commit()
    return jsonify(load=load.to_dict(), invoice=invoice.to_dict()), 201
