from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Account, ACCOUNT_TYPES
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("accounts", __name__)


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_accounts():
    accounts = scoped_query(Account).order_by(Account.code.asc()).all()
    return jsonify(accounts=[a.to_dict() for a in accounts])


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def create_account():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    type_ = data.get("type")

    if not code or not name or type_ not in ACCOUNT_TYPES:
        return jsonify(error="code, name, and a valid type are required"), 400

    if scoped_query(Account).filter_by(code=code).first():
        return jsonify(error="An account with that code already exists"), 409

    account = stamp_tenant(Account(
        code=code, name=name, type=type_,
        subtype=data.get("subtype"), parent_id=data.get("parent_id") or None,
    ))
    db.session.add(account)
    db.session.flush()
    log_action("account", account.id, "create", {"code": code, "name": name})
    db.session.commit()
    return jsonify(account=account.to_dict()), 201


@bp.patch("/<account_id>")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def update_account(account_id):
    account = scoped_query(Account).filter_by(id=account_id).first()
    if not account:
        return jsonify(error="Account not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("name", "subtype", "is_active"):
        if field in data:
            setattr(account, field, data[field])
            changes[field] = data[field]
    if "type" in data and data["type"] in ACCOUNT_TYPES:
        account.type = data["type"]
        changes["type"] = data["type"]

    log_action("account", account.id, "update", changes)
    db.session.commit()
    return jsonify(account=account.to_dict())


@bp.delete("/<account_id>")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def delete_account(account_id):
    account = scoped_query(Account).filter_by(id=account_id).first()
    if not account:
        return jsonify(error="Account not found"), 404
    account.soft_delete(user_id=g.user_id)
    log_action("account", account.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")
