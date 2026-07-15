from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Location
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("locations", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "warehouse_inventory")


@bp.get("")
@tenant_required
@module_required("inventory")
def list_locations():
    locations = scoped_query(Location).order_by(Location.name.asc()).all()
    return jsonify(locations=[l.to_dict() for l in locations])


@bp.post("")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def create_location():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400

    is_default = bool(data.get("is_default"))
    if is_default:
        scoped_query(Location).filter_by(is_default=True).update({"is_default": False})

    location = stamp_tenant(Location(
        name=name,
        address_line1=data.get("address_line1"),
        city=data.get("city"),
        state=data.get("state"),
        postal_code=data.get("postal_code"),
        is_default=is_default,
    ))
    db.session.add(location)
    db.session.flush()
    log_action("location", location.id, "create", {"name": name})
    db.session.commit()
    return jsonify(location=location.to_dict()), 201


@bp.patch("/<location_id>")
@tenant_required
@module_required("inventory")
@role_required(*WRITE_ROLES)
def update_location(location_id):
    location = scoped_query(Location).filter_by(id=location_id).first()
    if not location:
        return jsonify(error="Location not found"), 404

    data = request.get_json(silent=True) or {}
    for field in ("name", "address_line1", "city", "state", "postal_code", "is_active"):
        if field in data:
            setattr(location, field, data[field])
    if data.get("is_default"):
        scoped_query(Location).filter_by(is_default=True).update({"is_default": False})
        location.is_default = True

    log_action("location", location.id, "update", {})
    db.session.commit()
    return jsonify(location=location.to_dict())
