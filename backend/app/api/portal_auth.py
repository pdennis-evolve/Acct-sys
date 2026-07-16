import uuid

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity,
)

from app.models import Tenant, PortalUser, Customer

bp = Blueprint("portal_auth", __name__)


@bp.post("/login")
def login():
    """Mirrors the staff login shape (tenant resolves first, then auth is
    checked within that tenant's pool) but against PortalUser, not User,
    and gated on the tenant having the customer_portal module enabled."""
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

    if not tenant.has_module("customer_portal"):
        return jsonify(error="Customer portal is not enabled for this account"), 403

    portal_user = PortalUser.query.filter_by(tenant_id=tenant.id, email=email).first()
    if not portal_user or not portal_user.is_active or not portal_user.check_password(password):
        return jsonify(error="Invalid tenant, email, or password"), 401

    customer = Customer.query.filter_by(id=portal_user.customer_id, tenant_id=tenant.id).first()
    if not customer or not customer.is_active or customer.is_deleted:
        return jsonify(error="This portal login is no longer active"), 403

    from datetime import datetime, timezone
    from app.extensions import db

    portal_user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    claims = {
        "tenant_id": tenant.id,
        "customer_id": portal_user.customer_id,
        "is_portal_user": True,
    }
    access_token = create_access_token(identity=portal_user.id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=portal_user.id, additional_claims=claims)

    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        portal_user=portal_user.to_dict(),
        customer=customer.to_dict(include_contacts=False),
        tenant={"name": tenant.name, "slug": tenant.slug},
    )


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt()
    if not claims.get("is_portal_user"):
        return jsonify(error="Not a portal token"), 403
    identity = get_jwt_identity()
    new_claims = {
        "tenant_id": claims.get("tenant_id"),
        "customer_id": claims.get("customer_id"),
        "is_portal_user": True,
    }
    access_token = create_access_token(identity=identity, additional_claims=new_claims)
    return jsonify(access_token=access_token)


@bp.get("/me")
@jwt_required()
def me():
    claims = get_jwt()
    if not claims.get("is_portal_user"):
        return jsonify(error="Not a portal token"), 403
    identity = get_jwt_identity()
    portal_user = PortalUser.query.get(identity)
    customer = Customer.query.get(claims.get("customer_id")) if portal_user else None
    tenant = Tenant.query.get(claims.get("tenant_id")) if portal_user else None
    return jsonify(
        portal_user=portal_user.to_dict() if portal_user else None,
        customer=customer.to_dict(include_contacts=False) if customer else None,
        tenant={"name": tenant.name, "slug": tenant.slug} if tenant else None,
    )
