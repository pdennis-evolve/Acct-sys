from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import TaxRate
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("tax_rates", __name__)

WRITE_ROLES = ("owner_admin", "accountant")


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_tax_rates():
    rates = scoped_query(TaxRate).order_by(TaxRate.name.asc()).all()
    return jsonify(tax_rates=[r.to_dict() for r in rates])


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_tax_rate():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400
    try:
        rate = Decimal(str(data.get("rate", 0)))
    except InvalidOperation:
        return jsonify(error="rate must be numeric"), 400

    is_default = bool(data.get("is_default"))
    if is_default:
        scoped_query(TaxRate).filter_by(is_default=True).update({"is_default": False})

    tax_rate = stamp_tenant(TaxRate(
        name=name, rate=rate, jurisdiction=data.get("jurisdiction"), is_default=is_default,
    ))
    db.session.add(tax_rate)
    db.session.flush()
    log_action("tax_rate", tax_rate.id, "create", {"name": name, "rate": str(rate)})
    db.session.commit()
    return jsonify(tax_rate=tax_rate.to_dict()), 201


@bp.patch("/<tax_rate_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_tax_rate(tax_rate_id):
    tax_rate = scoped_query(TaxRate).filter_by(id=tax_rate_id).first()
    if not tax_rate:
        return jsonify(error="Tax rate not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    if "name" in data:
        tax_rate.name = data["name"]
        changes["name"] = data["name"]
    if "rate" in data:
        try:
            tax_rate.rate = Decimal(str(data["rate"]))
        except InvalidOperation:
            return jsonify(error="rate must be numeric"), 400
        changes["rate"] = str(tax_rate.rate)
    if "jurisdiction" in data:
        tax_rate.jurisdiction = data["jurisdiction"]
    if "is_active" in data:
        tax_rate.is_active = bool(data["is_active"])
    if "is_default" in data and bool(data["is_default"]):
        scoped_query(TaxRate).filter_by(is_default=True).update({"is_default": False})
        tax_rate.is_default = True

    log_action("tax_rate", tax_rate.id, "update", changes)
    db.session.commit()
    return jsonify(tax_rate=tax_rate.to_dict())


@bp.delete("/<tax_rate_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def delete_tax_rate(tax_rate_id):
    tax_rate = scoped_query(TaxRate).filter_by(id=tax_rate_id).first()
    if not tax_rate:
        return jsonify(error="Tax rate not found"), 404
    tax_rate.soft_delete()
    log_action("tax_rate", tax_rate.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")
