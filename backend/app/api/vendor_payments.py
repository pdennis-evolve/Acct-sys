from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import VendorPayment, VendorPaymentApplication, Bill, Vendor, CashAccount, CashTransaction, VENDOR_PAYMENT_METHODS
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("vendor_payments", __name__)

WRITE_ROLES = ("owner_admin", "accountant")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_vendor_payments():
    q = scoped_query(VendorPayment)
    vendor_id = request.args.get("vendor_id")
    if vendor_id:
        q = q.filter_by(vendor_id=vendor_id)
    payments = q.order_by(VendorPayment.payment_date.desc()).all()
    return jsonify(vendor_payments=[p.to_dict() for p in payments])


@bp.get("/<payment_id>")
@tenant_required
@module_required("ar_ap")
def get_vendor_payment(payment_id):
    payment = scoped_query(VendorPayment).filter_by(id=payment_id).first()
    if not payment:
        return jsonify(error="Vendor payment not found"), 404
    return jsonify(vendor_payment=payment.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_vendor_payment():
    """Pays down one or more approved bills. Only bills that have cleared
    the approval workflow (status approved/partial) are payable -- draft
    or pending_approval bills can't be paid out from under review."""
    data = request.get_json(silent=True) or {}

    vendor = scoped_query(Vendor).filter_by(id=data.get("vendor_id")).first()
    if not vendor:
        return jsonify(error="A valid vendor_id is required"), 400

    try:
        amount = Decimal(str(data.get("amount", 0)))
    except InvalidOperation:
        return jsonify(error="amount must be numeric"), 400
    if amount <= 0:
        return jsonify(error="amount must be greater than zero"), 400

    method = data.get("method") or "check"
    if method not in VENDOR_PAYMENT_METHODS:
        return jsonify(error="Invalid payment method"), 400

    cash_account = None
    cash_account_id = data.get("cash_account_id")
    if cash_account_id:
        cash_account = scoped_query(CashAccount).filter_by(id=cash_account_id).first()
        if not cash_account:
            return jsonify(error="cash_account_id not found"), 400

    applications_data = data.get("applications") or []
    total_applied = Decimal("0")
    resolved = []
    for app_row in applications_data:
        bill = scoped_query(Bill).filter_by(id=app_row.get("bill_id"), vendor_id=vendor.id).first()
        if not bill:
            return jsonify(error=f"Bill {app_row.get('bill_id')} not found for this vendor"), 400
        if bill.status not in ("approved", "partial"):
            return jsonify(error=f"Bill {bill.bill_number or bill.id} is not approved for payment"), 400
        try:
            amt = Decimal(str(app_row.get("amount_applied", 0)))
        except InvalidOperation:
            return jsonify(error="amount_applied must be numeric"), 400
        if amt <= 0:
            continue
        if amt > bill.balance_due:
            return jsonify(error=f"amount_applied exceeds balance due on bill {bill.bill_number or bill.id}"), 400
        resolved.append((bill, amt))
        total_applied += amt

    if total_applied > amount:
        return jsonify(error="Sum of applications exceeds payment amount"), 400

    payment = stamp_tenant(VendorPayment(
        vendor_id=vendor.id,
        cash_account_id=cash_account.id if cash_account else None,
        payment_date=_parse_date(data.get("payment_date"), datetime.utcnow().date()),
        amount=amount,
        method=method,
        reference_number=data.get("reference_number"),
        memo=data.get("memo"),
        created_by=g.user_id,
    ))
    db.session.add(payment)
    db.session.flush()

    for bill, amt in resolved:
        db.session.add(stamp_tenant(VendorPaymentApplication(
            vendor_payment_id=payment.id, bill_id=bill.id, amount_applied=amt,
        )))
        db.session.flush()
        bill.refresh_balance()
        bill.updated_by = g.user_id

    if cash_account:
        cash_account.current_balance = cash_account.current_balance - amount
        db.session.add(stamp_tenant(CashTransaction(
            cash_account_id=cash_account.id,
            txn_date=payment.payment_date,
            txn_type="withdrawal",
            amount=amount,
            payee=vendor.display_name,
            memo=data.get("memo") or f"Bill payment - {payment.reference_number or ''}".strip(),
            related_vendor_payment_id=payment.id,
        )))

    log_action("vendor_payment", payment.id, "create", {"amount": str(amount), "vendor_id": vendor.id})
    db.session.commit()
    return jsonify(vendor_payment=payment.to_dict()), 201


@bp.post("/<payment_id>/void")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def void_vendor_payment(payment_id):
    payment = scoped_query(VendorPayment).filter_by(id=payment_id).first()
    if not payment:
        return jsonify(error="Vendor payment not found"), 404

    affected_bills = [a.bill for a in payment.applications]
    for application in list(payment.applications):
        db.session.delete(application)
    db.session.flush()

    for bill in affected_bills:
        bill.refresh_balance()
        bill.updated_by = g.user_id

    if payment.cash_account_id:
        cash_account = scoped_query(CashAccount).filter_by(id=payment.cash_account_id).first()
        if cash_account:
            cash_account.current_balance = cash_account.current_balance + payment.amount

    payment.soft_delete(user_id=g.user_id)
    log_action("vendor_payment", payment.id, "void")
    db.session.commit()
    return jsonify(status="voided")
