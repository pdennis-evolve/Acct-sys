from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity


def role_required(*roles):
    """Server-side role gate. Must run after @tenant_required."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.get("role") not in roles:
                return jsonify(error="Insufficient role for this action"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def module_required(module_key):
    """Blocks a disabled module's endpoints even when called directly,
    not just hidden from nav. Must run after @tenant_required."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tenant = g.get("tenant")
            if not tenant or not tenant.has_module(module_key):
                return jsonify(error=f"Module '{module_key}' is not enabled for this tenant"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def super_admin_required(fn):
    """ETG-only cross-tenant endpoints. Independent of tenant_required."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get("is_super_admin"):
            return jsonify(error="Super-admin access required"), 403
        g.super_admin_id = get_jwt_identity()
        return fn(*args, **kwargs)

    return wrapper
