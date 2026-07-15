from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import Payment, PaymentApplication, Invoice, Customer, CashAccount, CashTransaction, PAYMENT_METHODS
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action

bp = Blueprint("payments", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "sales_ar_clerk")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_payments():
    q = scoped_query(Payment)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    payments = q.order_by(Payment.payment_date.desc()).all()
    return jsonify(payments=[p.to_dict() for p in payments])


@bp.get("/<payment_id>")
@tenant_required
@module_required("ar_ap")
def get_payment(payment_id):
    payment = scoped_query(Payment).filter_by(id=payment_id).first()
    if not payment:
        return jsonify(error="Payment not found"), 404
    return jsonify(payment=payment.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_payment():
    """Customer receipt: record money received and apply it across one or
    more invoices, supporting partial payments (unapplied balance allowed)."""
    data = request.get_json(silent=True) or {}

    customer = scoped_query(Customer).filter_by(id=data.get("customer_id")).first()
    if not customer:
        return jsonify(error="A valid customer_id is required"), 400

    try:
        amount = Decimal(str(data.get("amount", 0)))
    except InvalidOperation:
        return jsonify(error="amount must be numeric"), 400
    if amount <= 0:
        return jsonify(error="amount must be greater than zero"), 400

    method = data.get("method") or "check"
    if method not in PAYMENT_METHODS:
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
        invoice = scoped_query(Invoice).filter_by(id=app_row.get("invoice_id"), customer_id=customer.id).first()
        if not invoice:
            return jsonify(error=f"Invoice {app_row.get('invoice_id')} not found for this customer"), 400
        try:
            amt = Decimal(str(app_row.get("amount_applied", 0)))
        except InvalidOperation:
            return jsonify(error="amount_applied must be numeric"), 400
        if amt <= 0:
            continue
        if amt > invoice.balance_due:
            return jsonify(error=f"amount_applied exceeds balance due on invoice {invoice.invoice_number}"), 400
        resolved.append((invoice, amt))
        total_applied += amt

    if total_applied > amount:
        return jsonify(error="Sum of applications exceeds payment amount"), 400

    payment = stamp_tenant(Payment(
        customer_id=customer.id,
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

    for invoice, amt in resolved:
        db.session.add(stamp_tenant(PaymentApplication(
            payment_id=payment.id, invoice_id=invoice.id, amount_applied=amt,
        )))
        db.session.flush()
        invoice.refresh_balance()
        invoice.updated_by = g.user_id

    if cash_account:
        cash_account.current_balance = cash_account.current_balance + amount
        db.session.add(stamp_tenant(CashTransaction(
            cash_account_id=cash_account.id,
            txn_date=payment.payment_date,
            txn_type="deposit",
            amount=amount,
            payee=customer.display_name,
            memo=data.get("memo") or f"Payment received - {payment.reference_number or ''}".strip(),
            related_payment_id=payment.id,
        )))

    log_action("payment", payment.id, "create", {"amount": str(amount), "customer_id": customer.id})
    db.session.commit()
    return jsonify(payment=payment.to_dict()), 201


@bp.post("/<payment_id>/void")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def void_payment(payment_id):
    """Reverses applications (freeing invoice balances) and soft-deletes the
    receipt. Financial records are never hard-deleted."""
    payment = scoped_query(Payment).filter_by(id=payment_id).first()
    if not payment:
        return jsonify(error="Payment not found"), 404

    affected_invoices = [a.invoice for a in payment.applications]
    for application in list(payment.applications):
        db.session.delete(application)
    db.session.flush()

    for invoice in affected_invoices:
        invoice.refresh_balance()
        invoice.updated_by = g.user_id

    if payment.cash_account_id:
        cash_account = scoped_query(CashAccount).filter_by(id=payment.cash_account_id).first()
        if cash_account:
            cash_account.current_balance = cash_account.current_balance - payment.amount

    payment.soft_delete(user_id=g.user_id)
    log_action("payment", payment.id, "void")
    db.session.commit()
    return jsonify(status="voided")
