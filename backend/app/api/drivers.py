from datetime import datetime

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Driver, DRIVER_STATUSES
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("drivers", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "dispatcher")


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@tenant_required
@module_required("transportation")
def list_drivers():
    q = scoped_query(Driver)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    drivers = q.order_by(Driver.full_name.asc()).all()
    return jsonify(drivers=[d.to_dict() for d in drivers])


@bp.post("")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def create_driver():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        return jsonify(error="full_name is required"), 400

    driver = stamp_tenant(Driver(
        full_name=full_name,
        phone=data.get("phone"),
        email=data.get("email"),
        license_number=data.get("license_number"),
        license_class=data.get("license_class"),
        license_expiration=_parse_date(data.get("license_expiration")),
        notes=data.get("notes"),
        created_by=g.user_id,
    ))
    db.session.add(driver)
    db.session.flush()
    log_action("driver", driver.id, "create", {"full_name": full_name})
    db.session.commit()
    return jsonify(driver=driver.to_dict()), 201


@bp.patch("/<driver_id>")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def update_driver(driver_id):
    driver = scoped_query(Driver).filter_by(id=driver_id).first()
    if not driver:
        return jsonify(error="Driver not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("full_name", "phone", "email", "license_number", "license_class", "notes", "is_active"):
        if field in data:
            setattr(driver, field, data[field])
            changes[field] = data[field]
    if "license_expiration" in data:
        driver.license_expiration = _parse_date(data["license_expiration"])
    if "status" in data:
        if data["status"] not in DRIVER_STATUSES:
            return jsonify(error="Invalid status"), 400
        driver.status = data["status"]
        changes["status"] = data["status"]

    driver.updated_by = g.user_id
    log_action("driver", driver.id, "update", changes)
    db.session.commit()
    return jsonify(driver=driver.to_dict())


@bp.delete("/<driver_id>")
@tenant_required
@module_required("transportation")
@role_required(*WRITE_ROLES)
def delete_driver(driver_id):
    driver = scoped_query(Driver).filter_by(id=driver_id).first()
    if not driver:
        return jsonify(error="Driver not found"), 404
    driver.soft_delete(user_id=g.user_id)
    log_action("driver", driver.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")
