from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Customer, CustomerContact, PortalUser
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("customers", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "sales_ar_clerk")

ADDRESS_FIELDS = {
    "billing_address": ("billing_address_line1", "billing_address_line2", "billing_city", "billing_state", "billing_postal_code", "billing_country"),
    "shipping_address": ("shipping_address_line1", "shipping_address_line2", "shipping_city", "shipping_state", "shipping_postal_code", "shipping_country"),
}
ADDRESS_KEYS = ("line1", "line2", "city", "state", "postal_code", "country")


def _apply_address(customer, prefix, payload):
    if not payload:
        return
    for attr, key in zip(ADDRESS_FIELDS[prefix], ADDRESS_KEYS):
        if key in payload:
            setattr(customer, attr, payload[key])


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_customers():
    q = scoped_query(Customer)
    search = request.args.get("q")
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Customer.display_name.ilike(like), Customer.company_name.ilike(like)))
    customers = q.order_by(Customer.display_name.asc()).all()
    return jsonify(customers=[c.to_dict(include_contacts=False) for c in customers])


@bp.get("/<customer_id>")
@tenant_required
@module_required("ar_ap")
def get_customer(customer_id):
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404
    return jsonify(customer=customer.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_customer():
    data = request.get_json(silent=True) or {}
    display_name = (data.get("display_name") or "").strip()
    if not display_name:
        return jsonify(error="display_name is required"), 400

    customer = stamp_tenant(Customer(
        display_name=display_name,
        company_name=data.get("company_name"),
        email=data.get("email"),
        phone=data.get("phone"),
        notes=data.get("notes"),
        created_by=g.user_id,
    ))
    _apply_address(customer, "billing_address", data.get("billing_address"))
    _apply_address(customer, "shipping_address", data.get("shipping_address"))
    db.session.add(customer)
    db.session.flush()

    for contact in data.get("contacts") or []:
        if not contact.get("name"):
            continue
        db.session.add(stamp_tenant(CustomerContact(
            customer_id=customer.id,
            name=contact["name"],
            title=contact.get("title"),
            email=contact.get("email"),
            phone=contact.get("phone"),
            is_primary=bool(contact.get("is_primary")),
        )))

    log_action("customer", customer.id, "create", {"display_name": display_name})
    db.session.commit()
    return jsonify(customer=customer.to_dict()), 201


@bp.patch("/<customer_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_customer(customer_id):
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("display_name", "company_name", "email", "phone", "notes", "is_active"):
        if field in data:
            setattr(customer, field, data[field])
            changes[field] = data[field]
    if "billing_address" in data:
        _apply_address(customer, "billing_address", data["billing_address"])
        changes["billing_address"] = data["billing_address"]
    if "shipping_address" in data:
        _apply_address(customer, "shipping_address", data["shipping_address"])
        changes["shipping_address"] = data["shipping_address"]

    customer.updated_by = g.user_id
    log_action("customer", customer.id, "update", changes)
    db.session.commit()
    return jsonify(customer=customer.to_dict())


@bp.delete("/<customer_id>")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def delete_customer(customer_id):
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404
    customer.soft_delete(user_id=g.user_id)
    log_action("customer", customer.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")


@bp.post("/<customer_id>/contacts")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def add_contact(customer_id):
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify(error="name is required"), 400

    contact = stamp_tenant(CustomerContact(
        customer_id=customer.id,
        name=data["name"],
        title=data.get("title"),
        email=data.get("email"),
        phone=data.get("phone"),
        is_primary=bool(data.get("is_primary")),
    ))
    db.session.add(contact)
    db.session.commit()
    return jsonify(contact=contact.to_dict()), 201


@bp.get("/<customer_id>/portal-users")
@tenant_required
@module_required("customer_portal")
@role_required(*WRITE_ROLES)
def list_portal_users(customer_id):
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404
    portal_users = PortalUser.query.filter_by(tenant_id=g.tenant_id, customer_id=customer_id).all()
    return jsonify(portal_users=[p.to_dict() for p in portal_users])


@bp.post("/<customer_id>/portal-users")
@tenant_required
@module_required("customer_portal")
@role_required(*WRITE_ROLES)
def create_portal_user(customer_id):
    """Staff-initiated login provisioning for a customer's portal access.
    The initial password is set here and must be relayed to the customer
    out of band (email/phone) -- there is no self-service signup."""
    customer = scoped_query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return jsonify(error="Customer not found"), 404

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip()
    password = data.get("password") or ""
    if not email or not full_name or not password:
        return jsonify(error="email, full_name, and password are required"), 400
    if len(password) < 8:
        return jsonify(error="password must be at least 8 characters"), 400

    existing = PortalUser.query.filter_by(tenant_id=g.tenant_id, email=email).first()
    if existing:
        return jsonify(error="A portal login with this email already exists"), 409

    portal_user = PortalUser(
        tenant_id=g.tenant_id,
        customer_id=customer.id,
        email=email,
        full_name=full_name,
    )
    portal_user.set_password(password)
    db.session.add(portal_user)
    db.session.flush()
    log_action("portal_user", portal_user.id, "create", {"email": email, "customer_id": customer_id})
    db.session.commit()
    return jsonify(portal_user=portal_user.to_dict()), 201


@bp.patch("/<customer_id>/portal-users/<portal_user_id>")
@tenant_required
@module_required("customer_portal")
@role_required(*WRITE_ROLES)
def update_portal_user(customer_id, portal_user_id):
    portal_user = PortalUser.query.filter_by(
        id=portal_user_id, tenant_id=g.tenant_id, customer_id=customer_id
    ).first()
    if not portal_user:
        return jsonify(error="Portal login not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    if "full_name" in data:
        portal_user.full_name = data["full_name"]
        changes["full_name"] = data["full_name"]
    if "is_active" in data:
        portal_user.is_active = bool(data["is_active"])
        changes["is_active"] = portal_user.is_active
    if data.get("password"):
        if len(data["password"]) < 8:
            return jsonify(error="password must be at least 8 characters"), 400
        portal_user.set_password(data["password"])
        changes["password"] = "reset"

    log_action("portal_user", portal_user.id, "update", changes)
    db.session.commit()
    return jsonify(portal_user=portal_user.to_dict())
