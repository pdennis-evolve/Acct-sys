"""Every query against a tenant-scoped model must go through here.

Endpoints never filter by tenant_id by hand — that leaves it to each
author to remember, which is exactly the mistake this module exists to
prevent. `@tenant_required` populates flask.g with the caller's tenant
context from the JWT; `scoped_query` / `stamp_tenant` are the only
sanctioned way to read or write tenant-scoped rows.
"""

from functools import wraps

from flask import g, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

from app.models.tenant import Tenant


def tenant_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("is_super_admin"):
            return jsonify(error="Super-admin token cannot access tenant endpoints"), 403
        if claims.get("is_portal_user"):
            return jsonify(error="Portal token cannot access staff endpoints"), 403

        g.user_id = get_jwt_identity()
        g.tenant_id = claims.get("tenant_id")
        g.role = claims.get("role")
        g.is_super_admin = False

        if not g.tenant_id:
            return jsonify(error="No tenant context in token"), 403

        tenant = Tenant.query.get(g.tenant_id)
        if not tenant or not tenant.is_active:
            return jsonify(error="Tenant not found or inactive"), 403

        g.tenant = tenant

        if tenant.is_locked() and request.method not in ("GET", "HEAD", "OPTIONS"):
            return jsonify(error="Tenant license expired or locked; account is read-only"), 403

        return fn(*args, **kwargs)

    return wrapper


def scoped_query(model):
    """SELECT scoped to the current tenant, excluding soft-deleted rows."""
    q = model.query.filter_by(tenant_id=g.tenant_id)
    if hasattr(model, "is_deleted"):
        q = q.filter_by(is_deleted=False)
    return q


def stamp_tenant(instance):
    """Attach the current tenant to a newly-constructed model instance."""
    instance.tenant_id = g.tenant_id
    return instance


def get_or_404(model, obj_id):
    obj = scoped_query(model).filter_by(id=obj_id).first()
    return obj


def portal_required(fn):
    """Auth gate for the customer-facing portal -- a wholly separate claim
    space from staff/super-admin tokens (see auth.py vs portal_auth.py).
    Populates g.tenant_id AND g.customer_id; every portal data endpoint
    must filter by both so one customer can never see another's records
    within the same tenant."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get("is_portal_user"):
            return jsonify(error="Staff or super-admin token cannot access portal endpoints"), 403

        g.portal_user_id = get_jwt_identity()
        g.tenant_id = claims.get("tenant_id")
        g.customer_id = claims.get("customer_id")

        if not g.tenant_id or not g.customer_id:
            return jsonify(error="No tenant/customer context in token"), 403

        tenant = Tenant.query.get(g.tenant_id)
        if not tenant or not tenant.is_active:
            return jsonify(error="Tenant not found or inactive"), 403
        if not tenant.has_module("customer_portal"):
            return jsonify(error="Customer portal is not enabled for this tenant"), 403

        g.tenant = tenant

        return fn(*args, **kwargs)

    return wrapper


def portal_scoped_query(model):
    """SELECT scoped to the current tenant AND the logged-in portal user's
    own customer -- the cross-customer isolation boundary for the portal."""
    q = model.query.filter_by(tenant_id=g.tenant_id, customer_id=g.customer_id)
    if hasattr(model, "is_deleted"):
        q = q.filter_by(is_deleted=False)
    return q
