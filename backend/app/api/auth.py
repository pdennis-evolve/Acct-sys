import uuid

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity,
)

from app.models import Tenant, User, SuperAdmin

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    """Tenant resolves first, then auth is checked within that tenant's user
    pool -- never a global email-uniqueness index across tenants."""
    data = request.get_json(silent=True) or {}
    tenant_key = (data.get("tenant") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not tenant_key or not email or not password:
        return jsonify(error="tenant, email, and password are required"), 400

    try:
        uuid.UUID(tenant_key)
        tenant = Tenant.query.filter(
            (Tenant.slug == tenant_key) | (Tenant.id == tenant_key)
        ).first()
    except ValueError:
        tenant = Tenant.query.filter_by(slug=tenant_key).first()
    if not tenant or not tenant.is_active:
        return jsonify(error="Invalid tenant, email, or password"), 401

    user = User.query.filter_by(tenant_id=tenant.id, email=email).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify(error="Invalid tenant, email, or password"), 401

    claims = {"tenant_id": tenant.id, "role": user.role, "is_super_admin": False}
    access_token = create_access_token(identity=user.id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=user.id, additional_claims=claims)

    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user.to_dict(),
        tenant=tenant.to_dict(),
    )


@bp.post("/superadmin/login")
def superadmin_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    admin = SuperAdmin.query.filter_by(email=email).first()
    if not admin or not admin.is_active or not admin.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    claims = {"is_super_admin": True}
    access_token = create_access_token(identity=admin.id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=admin.id, additional_claims=claims)

    return jsonify(access_token=access_token, refresh_token=refresh_token, admin=admin.to_dict())


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt()
    identity = get_jwt_identity()
    new_claims = {
        "tenant_id": claims.get("tenant_id"),
        "role": claims.get("role"),
        "is_super_admin": claims.get("is_super_admin", False),
    }
    access_token = create_access_token(identity=identity, additional_claims=new_claims)
    return jsonify(access_token=access_token)


@bp.get("/me")
@jwt_required()
def me():
    claims = get_jwt()
    identity = get_jwt_identity()
    if claims.get("is_super_admin"):
        admin = SuperAdmin.query.get(identity)
        return jsonify(admin=admin.to_dict() if admin else None, is_super_admin=True)

    user = User.query.get(identity)
    tenant = Tenant.query.get(claims.get("tenant_id")) if user else None
    return jsonify(
        user=user.to_dict() if user else None,
        tenant=tenant.to_dict() if tenant else None,
        is_super_admin=False,
    )
