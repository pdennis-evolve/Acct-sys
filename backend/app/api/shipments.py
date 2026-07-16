from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Shipment, SHIPMENT_REFERENCE_TYPES, SHIPMENT_STATUSES, CARRIERS, PurchaseOrder, Invoice, Load
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.carrier import detect_carrier, poll_status

bp = Blueprint("shipments", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "dispatcher", "warehouse_inventory")

_REFERENCE_MODELS = {
    "purchase_order": PurchaseOrder,
    "invoice": Invoice,
    "load": Load,
}


@bp.get("")
@tenant_required
@module_required("order_tracking")
def list_shipments():
    q = scoped_query(Shipment)
    reference_type = request.args.get("reference_type")
    reference_id = request.args.get("reference_id")
    if reference_type:
        q = q.filter_by(reference_type=reference_type)
    if reference_id:
        q = q.filter_by(reference_id=reference_id)
    shipments = q.order_by(Shipment.created_at.desc()).all()
    return jsonify(shipments=[s.to_dict() for s in shipments])


@bp.get("/<shipment_id>")
@tenant_required
@module_required("order_tracking")
def get_shipment(shipment_id):
    shipment = scoped_query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        return jsonify(error="Shipment not found"), 404
    return jsonify(shipment=shipment.to_dict())


@bp.post("")
@tenant_required
@module_required("order_tracking")
@role_required(*WRITE_ROLES)
def create_shipment():
    data = request.get_json(silent=True) or {}
    reference_type = data.get("reference_type")
    reference_id = data.get("reference_id")
    tracking_number = (data.get("tracking_number") or "").strip()

    if reference_type not in SHIPMENT_REFERENCE_TYPES:
        return jsonify(error=f"reference_type must be one of: {', '.join(SHIPMENT_REFERENCE_TYPES)}"), 400
    if not reference_id:
        return jsonify(error="reference_id is required"), 400
    if not tracking_number:
        return jsonify(error="tracking_number is required"), 400

    model = _REFERENCE_MODELS[reference_type]
    if not scoped_query(model).filter_by(id=reference_id).first():
        return jsonify(error=f"No {reference_type} found with that id"), 404

    carrier = data.get("carrier")
    if carrier and carrier not in CARRIERS:
        return jsonify(error="Invalid carrier"), 400
    if not carrier:
        carrier = detect_carrier(tracking_number)

    shipment = stamp_tenant(Shipment(
        reference_type=reference_type,
        reference_id=reference_id,
        tracking_number=tracking_number,
        carrier=carrier,
        status=data.get("status") if data.get("status") in SHIPMENT_STATUSES else "pending",
        status_source="manual",
        status_note=data.get("status_note"),
        created_by=g.user_id,
    ))
    db.session.add(shipment)
    db.session.flush()
    log_action("shipment", shipment.id, "create", {"tracking_number": tracking_number, "carrier": carrier})
    db.session.commit()
    return jsonify(shipment=shipment.to_dict()), 201


@bp.patch("/<shipment_id>")
@tenant_required
@module_required("order_tracking")
@role_required(*WRITE_ROLES)
def update_shipment(shipment_id):
    shipment = scoped_query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        return jsonify(error="Shipment not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    if "tracking_number" in data:
        tn = (data["tracking_number"] or "").strip()
        if not tn:
            return jsonify(error="tracking_number cannot be blank"), 400
        shipment.tracking_number = tn
        shipment.carrier = data.get("carrier") or detect_carrier(tn)
        changes["tracking_number"] = tn
    elif "carrier" in data:
        if data["carrier"] not in CARRIERS:
            return jsonify(error="Invalid carrier"), 400
        shipment.carrier = data["carrier"]
        changes["carrier"] = data["carrier"]
    if "status" in data:
        if data["status"] not in SHIPMENT_STATUSES:
            return jsonify(error="Invalid status"), 400
        shipment.status = data["status"]
        shipment.status_source = "manual"
        changes["status"] = data["status"]
    if "status_note" in data:
        shipment.status_note = data["status_note"]

    shipment.updated_by = g.user_id
    log_action("shipment", shipment.id, "update", changes)
    db.session.commit()
    return jsonify(shipment=shipment.to_dict())


@bp.delete("/<shipment_id>")
@tenant_required
@module_required("order_tracking")
@role_required(*WRITE_ROLES)
def delete_shipment(shipment_id):
    shipment = scoped_query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        return jsonify(error="Shipment not found"), 404
    log_action("shipment", shipment.id, "delete")
    db.session.delete(shipment)
    db.session.commit()
    return jsonify(status="deleted")


@bp.post("/<shipment_id>/refresh")
@tenant_required
@module_required("order_tracking")
@role_required(*WRITE_ROLES)
def refresh_shipment(shipment_id):
    """Attempts a live carrier status poll. Honestly reports when no
    carrier API is configured rather than fabricating a status."""
    shipment = scoped_query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        return jsonify(error="Shipment not found"), 404

    ok, status, note = poll_status(shipment)
    shipment.last_checked_at = datetime.now(timezone.utc)
    if ok and status:
        shipment.status = status
        shipment.status_source = "carrier_api"
    shipment.status_note = note
    db.session.commit()
    return jsonify(shipment=shipment.to_dict(), polled=ok)
