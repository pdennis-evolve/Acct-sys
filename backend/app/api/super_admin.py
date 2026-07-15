from datetime import datetime

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Tenant, User, ALL_MODULES, DEFAULT_MODULES
from app.utils.decorators import super_admin_required

bp = Blueprint("super_admin", __name__)


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("/tenants")
@super_admin_required
def list_tenants():
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()
    out = []
    for t in tenants:
        d = t.to_dict()
        d["seats_used"] = User.query.filter_by(tenant_id=t.id, is_active=True).count()
        out.append(d)
    return jsonify(tenants=out)


@bp.post("/tenants")
@super_admin_required
def create_tenant():
    """Provisioning flow: create tenant, toggle module set, set seat count
    and license duration, and bootstrap the first Owner/Admin user."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or "").strip().lower()
    if not name or not slug:
        return jsonify(error="name and slug are required"), 400

    if Tenant.query.filter_by(slug=slug).first():
        return jsonify(error="A tenant with that slug already exists"), 409

    modules = dict(DEFAULT_MODULES)
    for key, val in (data.get("modules") or {}).items():
        if key in ALL_MODULES:
            modules[key] = bool(val)

    tenant = Tenant(
        name=name,
        slug=slug,
        modules=modules,
        seat_limit=int(data.get("seat_limit") or 5),
        license_status=data.get("license_status") or "trial",
        license_start=_parse_date(data.get("license_start")),
        license_end=_parse_date(data.get("license_end")),
        grace_period_days=int(data.get("grace_period_days") or 14),
        plan_notes=data.get("plan_notes"),
    )
    db.session.add(tenant)
    db.session.flush()

    admin_email = (data.get("admin_email") or "").strip().lower()
    admin_password = data.get("admin_password") or ""
    admin_name = data.get("admin_name") or "Admin"
    if admin_email and admin_password:
        owner = User(
            tenant_id=tenant.id,
            email=admin_email,
            full_name=admin_name,
            role="owner_admin",
        )
        owner.set_password(admin_password)
        db.session.add(owner)

    db.session.commit()
    return jsonify(tenant=tenant.to_dict()), 201


@bp.get("/tenants/<tenant_id>")
@super_admin_required
def get_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify(error="Tenant not found"), 404
    d = tenant.to_dict()
    d["seats_used"] = User.query.filter_by(tenant_id=tenant.id, is_active=True).count()
    return jsonify(tenant=d)


@bp.patch("/tenants/<tenant_id>")
@super_admin_required
def update_tenant(tenant_id):
    """Toggle module set, seat limit, license duration/status independently."""
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify(error="Tenant not found"), 404

    data = request.get_json(silent=True) or {}

    if "name" in data:
        tenant.name = data["name"]
    if "modules" in data:
        modules = dict(tenant.modules or {})
        for key, val in (data["modules"] or {}).items():
            if key in ALL_MODULES:
                modules[key] = bool(val)
        tenant.modules = modules
    if "seat_limit" in data:
        tenant.seat_limit = int(data["seat_limit"])
    if "license_status" in data:
        tenant.license_status = data["license_status"]
    if "license_start" in data:
        tenant.license_start = _parse_date(data["license_start"])
    if "license_end" in data:
        tenant.license_end = _parse_date(data["license_end"])
    if "grace_period_days" in data:
        tenant.grace_period_days = int(data["grace_period_days"])
    if "plan_notes" in data:
        tenant.plan_notes = data["plan_notes"]
    if "is_active" in data:
        tenant.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify(tenant=tenant.to_dict())
