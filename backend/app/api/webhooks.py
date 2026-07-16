"""Authorize.net webhook receiver (brief Phase 9: "webhook layer for
payment processor"). This sandbox has no live Authorize.net merchant
account -- AUTHORIZE_NET_SIGNATURE_KEY is unset -- so the honest path
(501, signature verification never even attempted) is the only one that
actually runs here. The signature-verification and reconciliation logic
below is real and is the path a live deployment runs once a merchant
account is configured; it is simply unexercised for lack of credentials.

Reconciliation matches on `merchantReferenceId`, which the (not yet live,
since it requires the same missing credentials) checkout flow would set
to the paying Invoice's id when creating the Authorize.net transaction
request -- so the id is globally unique and no tenant needs to be
encoded in the webhook URL itself.
"""
import hashlib
import hmac

from flask import Blueprint, request, jsonify, current_app

from app.extensions import db
from app.models import Invoice, Payment, PaymentApplication

bp = Blueprint("webhooks", __name__)

# Event types that represent money actually landing -- everything else
# (fraud holds, refunds, voids) is acknowledged but not reconciled here;
# extending that is real future work, not something fakeable without a
# live account to observe real payloads from.
SETTLED_EVENT_TYPES = {
    "net.authorize.payment.authcapture.created",
    "net.authorize.payment.capture.created",
}


def _is_configured() -> bool:
    return bool(current_app.config.get("AUTHORIZE_NET_SIGNATURE_KEY"))


def _verify_signature(raw_body: bytes, header_value: str | None) -> bool:
    if not header_value:
        return False
    key = current_app.config["AUTHORIZE_NET_SIGNATURE_KEY"]
    expected = hmac.new(key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    provided = header_value.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected.lower(), provided.lower())


@bp.post("/authorize-net")
def authorize_net_webhook():
    if not _is_configured():
        return jsonify(
            error="Authorize.net is not configured for this environment. "
                  "No merchant account/signature key is on file, so this webhook cannot be verified."
        ), 501

    raw_body = request.get_data()
    if not _verify_signature(raw_body, request.headers.get("X-ANET-Signature")):
        return jsonify(error="Invalid webhook signature"), 401

    event = request.get_json(silent=True) or {}
    event_type = event.get("eventType")
    payload = event.get("payload", {})

    if event_type not in SETTLED_EVENT_TYPES:
        return jsonify(status="acknowledged", reconciled=False), 200

    invoice_id = payload.get("merchantReferenceId")
    amount = payload.get("authAmount")
    trans_id = payload.get("transId")
    if not invoice_id or amount is None:
        current_app.logger.warning("Authorize.net webhook missing merchantReferenceId/authAmount: %s", event)
        return jsonify(status="acknowledged", reconciled=False), 200

    invoice = Invoice.query.filter_by(id=invoice_id, is_deleted=False).first()
    if not invoice:
        current_app.logger.warning("Authorize.net webhook referenced unknown invoice %s", invoice_id)
        return jsonify(status="acknowledged", reconciled=False), 200

    from decimal import Decimal
    from datetime import date

    amount = Decimal(str(amount))
    applied_amount = min(amount, invoice.balance_due) if invoice.balance_due > 0 else amount

    payment = Payment(
        tenant_id=invoice.tenant_id,
        customer_id=invoice.customer_id,
        payment_date=date.today(),
        amount=amount,
        method="credit_card",
        reference_number=trans_id,
        memo="Authorize.net online payment (customer portal)",
    )
    db.session.add(payment)
    db.session.flush()

    db.session.add(PaymentApplication(
        tenant_id=invoice.tenant_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount_applied=applied_amount,
    ))
    invoice.refresh_balance()
    db.session.commit()

    return jsonify(status="reconciled", invoice_id=invoice.id, payment_id=payment.id), 200
