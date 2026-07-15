from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import User, ROLES
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required
from app.services.audit import log_action

bp = Blueprint("users", __name__)


@bp.get("")
@tenant_required
@role_required("owner_admin")
def list_users():
    users = scoped_query(User).order_by(User.created_at.asc()).all()
    return jsonify(
        users=[u.to_dict() for u in users],
        seats_used=len(users),
        seat_limit=g.tenant.seat_limit,
    )


@bp.post("")
@tenant_required
@role_required("owner_admin")
def create_user():
    """Seat enforcement: block new user creation past the licensed count."""
    active_count = scoped_query(User).filter_by(is_active=True).count()
    if active_count >= g.tenant.seat_limit:
        return jsonify(error="Seat limit reached for this tenant's license"), 403

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = data.get("role")

    if not email or not password or not full_name or role not in ROLES:
        return jsonify(error="email, password, full_name, and a valid role are required"), 400

    if scoped_query(User).filter_by(email=email).first():
        return jsonify(error="A user with that email already exists in this tenant"), 409

    user = stamp_tenant(User(email=email, full_name=full_name, role=role))
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    log_action("user", user.id, "create", {"email": email, "role": role})
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@bp.patch("/<user_id>")
@tenant_required
@role_required("owner_admin")
def update_user(user_id):
    user = scoped_query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify(error="User not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    if "full_name" in data:
        user.full_name = data["full_name"]
        changes["full_name"] = data["full_name"]
    if "role" in data and data["role"] in ROLES:
        user.role = data["role"]
        changes["role"] = data["role"]
    if "is_active" in data:
        if bool(data["is_active"]) and not user.is_active:
            active_count = scoped_query(User).filter_by(is_active=True).count()
            if active_count >= g.tenant.seat_limit:
                return jsonify(error="Seat limit reached for this tenant's license"), 403
        user.is_active = bool(data["is_active"])
        changes["is_active"] = user.is_active
    if data.get("password"):
        user.set_password(data["password"])
        changes["password"] = "changed"

    log_action("user", user.id, "update", changes)
    db.session.commit()
    return jsonify(user=user.to_dict())
