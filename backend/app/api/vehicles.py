from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Vehicle, VEHICLE_TYPES, VEHICLE_STATUSES
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("vehicles", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "dispatcher")


@bp.get("")
@tenant_required
@module_required("transportation")
def list_vehicles():
    q = scoped_query(Vehicle)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    vehicles = q.order_by(Vehicle.unit_number.asc()).all()
    return jsonify(vehicles=[v.to_dict() for v in vehicles])


@bp.post("")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def create_vehicle():
    data = request.get_json(silent=True) or {}
    unit_number = (data.get("unit_number") or "").strip()
    if not unit_number:
        return jsonify(error="unit_number is required"), 400
    vehicle_type = data.get("vehicle_type") or "truck"
    if vehicle_type not in VEHICLE_TYPES:
        return jsonify(error="Invalid vehicle_type"), 400

    if scoped_query(Vehicle).filter_by(unit_number=unit_number).first():
        return jsonify(error="A vehicle with that unit number already exists"), 409

    vehicle = stamp_tenant(Vehicle(
        unit_number=unit_number,
        vehicle_type=vehicle_type,
        make=data.get("make"),
        model=data.get("model"),
        year=data.get("year") or None,
        vin=data.get("vin"),
        license_plate=data.get("license_plate"),
        notes=data.get("notes"),
        created_by=g.user_id,
    ))
    db.session.add(vehicle)
    db.session.flush()
    log_action("vehicle", vehicle.id, "create", {"unit_number": unit_number})
    db.session.commit()
    return jsonify(vehicle=vehicle.to_dict()), 201


@bp.patch("/<vehicle_id>")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def update_vehicle(vehicle_id):
    vehicle = scoped_query(Vehicle).filter_by(id=vehicle_id).first()
    if not vehicle:
        return jsonify(error="Vehicle not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("make", "model", "vin", "license_plate", "notes", "is_active"):
        if field in data:
            setattr(vehicle, field, data[field])
            changes[field] = data[field]
    if "year" in data:
        vehicle.year = data["year"] or None
    if "status" in data:
        if data["status"] not in VEHICLE_STATUSES:
            return jsonify(error="Invalid status"), 400
        vehicle.status = data["status"]
        changes["status"] = data["status"]

    vehicle.updated_by = g.user_id
    log_action("vehicle", vehicle.id, "update", changes)
    db.session.commit()
    return jsonify(vehicle=vehicle.to_dict())


@bp.delete("/<vehicle_id>")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def delete_vehicle(vehicle_id):
    vehicle = scoped_query(Vehicle).filter_by(id=vehicle_id).first()
    if not vehicle:
        return jsonify(error="Vehicle not found"), 404
    vehicle.soft_delete(user_id=g.user_id)
    log_action("vehicle", vehicle.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")
