from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Vendor, VendorContact
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("vendors", __name__)

WRITE_ROLES = ("owner_admin", "accountant")

ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "postal_code", "country")
ADDRESS_KEYS = ("line1", "line2", "city", "state", "postal_code", "country")


def _apply_address(vendor, payload):
    if not payload:
        return
    for attr, key in zip(ADDRESS_FIELDS, ADDRESS_KEYS):
        if key in payload:
            setattr(vendor, attr, payload[key])


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_vendors():
    q = scoped_query(Vendor)
    search = request.args.get("q")
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Vendor.display_name.ilike(like), Vendor.company_name.ilike(like)))
    vendors = q.order_by(Vendor.display_name.asc()).all()
    return jsonify(vendors=[v.to_dict(include_contacts=False) for v in vendors])


@bp.get("/<vendor_id>")
@tenant_required
@module_required("ar_ap")
def get_vendor(vendor_id):
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify(error="Vendor not found"), 404
    return jsonify(vendor=vendor.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_vendor():
    data = request.get_json(silent=True) or {}
    display_name = (data.get("display_name") or "").strip()
    if not display_name:
        return jsonify(error="display_name is required"), 400

    vendor = stamp_tenant(Vendor(
        display_name=display_name,
        company_name=data.get("company_name"),
        email=data.get("email"),
        phone=data.get("phone"),
        default_expense_account_id=data.get("default_expense_account_id") or None,
        notes=data.get("notes"),
        created_by=g.user_id,
    ))
    _apply_address(vendor, data.get("address"))
    db.session.add(vendor)
    db.session.flush()

    for contact in data.get("contacts") or []:
        if not contact.get("name"):
            continue
        db.session.add(stamp_tenant(VendorContact(
            vendor_id=vendor.id,
            name=contact["name"],
            title=contact.get("title"),
            email=contact.get("email"),
            phone=contact.get("phone"),
            is_primary=bool(contact.get("is_primary")),
        )))

    log_action("vendor", vendor.id, "create", {"display_name": display_name})
    db.session.commit()
    return jsonify(vendor=vendor.to_dict()), 201


@bp.patch("/<vendor_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_vendor(vendor_id):
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify(error="Vendor not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("display_name", "company_name", "email", "phone", "notes", "is_active"):
        if field in data:
            setattr(vendor, field, data[field])
            changes[field] = data[field]
    if "default_expense_account_id" in data:
        vendor.default_expense_account_id = data["default_expense_account_id"] or None
    if "address" in data:
        _apply_address(vendor, data["address"])
        changes["address"] = data["address"]

    vendor.updated_by = g.user_id
    log_action("vendor", vendor.id, "update", changes)
    db.session.commit()
    return jsonify(vendor=vendor.to_dict())


@bp.delete("/<vendor_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def delete_vendor(vendor_id):
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify(error="Vendor not found"), 404
    vendor.soft_delete(user_id=g.user_id)
    log_action("vendor", vendor.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")


@bp.post("/<vendor_id>/contacts")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def add_contact(vendor_id):
    vendor = scoped_query(Vendor).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify(error="Vendor not found"), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify(error="name is required"), 400

    contact = stamp_tenant(VendorContact(
        vendor_id=vendor.id,
        name=data["name"],
        title=data.get("title"),
        email=data.get("email"),
        phone=data.get("phone"),
        is_primary=bool(data.get("is_primary")),
    ))
    db.session.add(contact)
    db.session.commit()
    return jsonify(contact=contact.to_dict()), 201
