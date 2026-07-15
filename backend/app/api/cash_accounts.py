from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import CashAccount, CashTransaction, CASH_ACCOUNT_TYPES, CASH_TXN_TYPES
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("cash_accounts", __name__)

WRITE_ROLES = ("owner_admin", "accountant")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_cash_accounts():
    accounts = scoped_query(CashAccount).order_by(CashAccount.name.asc()).all()
    return jsonify(cash_accounts=[a.to_dict() for a in accounts])


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_cash_account():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    account_type = data.get("account_type") or "checking"
    if not name or account_type not in CASH_ACCOUNT_TYPES:
        return jsonify(error="name and a valid account_type are required"), 400

    try:
        opening_balance = Decimal(str(data.get("opening_balance", 0)))
    except InvalidOperation:
        opening_balance = Decimal("0")

    account = stamp_tenant(CashAccount(
        name=name,
        account_type=account_type,
        bank_name=data.get("bank_name"),
        account_number_last4=(data.get("account_number_last4") or "")[-4:] or None,
        gl_account_id=data.get("gl_account_id") or None,
        current_balance=opening_balance,
    ))
    db.session.add(account)
    db.session.flush()
    log_action("cash_account", account.id, "create", {"name": name})
    db.session.commit()
    return jsonify(cash_account=account.to_dict()), 201


@bp.get("/<account_id>/register")
@tenant_required
@module_required("ar_ap")
def register(account_id):
    account = scoped_query(CashAccount).filter_by(id=account_id).first()
    if not account:
        return jsonify(error="Cash account not found"), 404
    txns = scoped_query(CashTransaction).filter_by(
        cash_account_id=account.id
    ).order_by(CashTransaction.txn_date.desc(), CashTransaction.created_at.desc()).all()
    return jsonify(cash_account=account.to_dict(), transactions=[t.to_dict() for t in txns])


@bp.post("/<account_id>/register")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def add_transaction(account_id):
    """Manual check register entry (deposit/withdrawal/check), independent
    of the automatic entries payments/bill-payments create."""
    account = scoped_query(CashAccount).filter_by(id=account_id).first()
    if not account:
        return jsonify(error="Cash account not found"), 404

    data = request.get_json(silent=True) or {}
    txn_type = data.get("txn_type")
    if txn_type not in CASH_TXN_TYPES:
        return jsonify(error="A valid txn_type is required"), 400

    try:
        amount = Decimal(str(data.get("amount", 0)))
    except InvalidOperation:
        return jsonify(error="amount must be numeric"), 400
    if amount <= 0:
        return jsonify(error="amount must be greater than zero"), 400

    txn = stamp_tenant(CashTransaction(
        cash_account_id=account.id,
        txn_date=_parse_date(data.get("txn_date"), datetime.utcnow().date()),
        txn_type=txn_type,
        amount=amount,
        payee=data.get("payee"),
        memo=data.get("memo"),
        check_number=data.get("check_number"),
    ))
    db.session.add(txn)

    if txn_type == "deposit":
        account.current_balance = account.current_balance + amount
    else:
        account.current_balance = account.current_balance - amount

    log_action("cash_transaction", txn.id, "create", {"txn_type": txn_type, "amount": str(amount)})
    db.session.commit()
    return jsonify(transaction=txn.to_dict(), cash_account=account.to_dict()), 201
