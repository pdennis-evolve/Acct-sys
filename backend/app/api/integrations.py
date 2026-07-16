from flask import Blueprint, request, jsonify, g, redirect, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import db
from app.models import EmailConnection, User
from app.middleware.tenant_scope import tenant_required
from app.services import email_oauth

bp = Blueprint("integrations", __name__)

PROVIDERS = ("microsoft", "google")


def _state_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="email-oauth-state")


@bp.get("")
@tenant_required
def get_status():
    connections = {
        c.provider: c for c in EmailConnection.query.filter_by(tenant_id=g.tenant_id, user_id=g.user_id).all()
    }
    result = {}
    for provider in PROVIDERS:
        conn = connections.get(provider)
        result[provider] = {
            "configured": email_oauth.is_configured(provider),
            "connected": conn is not None,
            "email_address": conn.email_address if conn else None,
        }
    result["authorize_net"] = {
        "configured": bool(
            current_app.config.get("AUTHORIZE_NET_API_LOGIN_ID")
            and current_app.config.get("AUTHORIZE_NET_TRANSACTION_KEY")
        ),
    }
    return jsonify(integrations=result)


@bp.get("/<provider>/connect")
@tenant_required
def connect(provider):
    if provider not in PROVIDERS:
        return jsonify(error="Unknown provider"), 404
    if not email_oauth.is_configured(provider):
        return jsonify(
            error=f"{provider.title()} is not configured for this environment. "
                  f"An administrator must supply OAuth client credentials before this can be connected.",
            configured=False,
        ), 501

    state = _state_serializer().dumps({"tenant_id": g.tenant_id, "user_id": g.user_id, "provider": provider})
    authorize_url = email_oauth.build_authorize_url(provider, state)
    return jsonify(authorize_url=authorize_url)


@bp.get("/<provider>/callback")
def callback(provider):
    """Hit directly by the browser after the Microsoft/Google consent
    screen redirects back -- no JWT header available here, so the tenant
    and user context travels in the signed `state` param instead."""
    frontend_url = f"{current_app.config['APP_BASE_URL']}/settings/integrations"

    if provider not in PROVIDERS:
        return redirect(f"{frontend_url}?error=unknown_provider")

    error = request.args.get("error")
    if error:
        return redirect(f"{frontend_url}?error={error}")

    state = request.args.get("state", "")
    code = request.args.get("code")
    if not code:
        return redirect(f"{frontend_url}?error=missing_code")

    try:
        payload = _state_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        return redirect(f"{frontend_url}?error=invalid_state")

    if payload.get("provider") != provider:
        return redirect(f"{frontend_url}?error=invalid_state")

    try:
        token_data = email_oauth.exchange_code(provider, code)
    except email_oauth.IntegrationNotConfigured:
        return redirect(f"{frontend_url}?error=not_configured")
    except Exception:
        current_app.logger.exception("OAuth code exchange failed for %s", provider)
        return redirect(f"{frontend_url}?error=exchange_failed")

    conn = EmailConnection.query.filter_by(
        tenant_id=payload["tenant_id"], user_id=payload["user_id"], provider=provider
    ).first()
    if not conn:
        conn = EmailConnection(tenant_id=payload["tenant_id"], user_id=payload["user_id"], provider=provider)
        db.session.add(conn)

    conn.email_address = token_data["email_address"]
    conn.access_token = token_data["access_token"]
    conn.refresh_token = token_data.get("refresh_token") or conn.refresh_token
    conn.token_expires_at = token_data["expires_at"]
    db.session.commit()

    return redirect(f"{frontend_url}?connected={provider}")


@bp.delete("/<provider>")
@tenant_required
def disconnect(provider):
    if provider not in PROVIDERS:
        return jsonify(error="Unknown provider"), 404
    conn = EmailConnection.query.filter_by(tenant_id=g.tenant_id, user_id=g.user_id, provider=provider).first()
    if conn:
        db.session.delete(conn)
        db.session.commit()
    return jsonify(status="disconnected")
