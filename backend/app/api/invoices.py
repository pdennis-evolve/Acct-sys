from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g, Response

from app.extensions import db
from app.models import Invoice, InvoiceLine, Customer, CompanySettings, TaxRate
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.pdf import render_invoice_pdf

bp = Blueprint("invoices", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "sales_ar_clerk")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _apply_lines(invoice, lines_data):
    invoice.lines.clear()
    for i, line in enumerate(lines_data or []):
        try:
            qty = Decimal(str(line.get("quantity", 1)))
            price = Decimal(str(line.get("unit_price", 0)))
        except InvalidOperation:
            continue
        amount = (qty * price).quantize(Decimal("0.01"))
        invoice.lines.append(InvoiceLine(
            tenant_id=g.tenant_id,
            description=line.get("description", ""),
            quantity=qty,
            unit_price=price,
            amount=amount,
            account_id=line.get("account_id") or None,
            sort_order=i,
        ))


def _resolve_tax(data):
    """Returns (tax_rate_pct, tax_rate_id). Explicit tax_rate_id wins (looks
    up the persisted rate); a raw tax_rate falls back to an ad-hoc
    percentage with no jurisdiction attached; otherwise the tenant's
    default TaxRate applies; otherwise 0."""
    tax_rate_id = data.get("tax_rate_id")
    if tax_rate_id:
        rate_row = scoped_query(TaxRate).filter_by(id=tax_rate_id).first()
        if not rate_row:
            return None, "tax_rate_id not found"
        return (rate_row.rate, rate_row.id), None
    if "tax_rate" in data:
        try:
            return (Decimal(str(data.get("tax_rate", 0))), None), None
        except InvalidOperation:
            return None, "tax_rate must be numeric"
    default_rate = scoped_query(TaxRate).filter_by(is_default=True).first()
    if default_rate:
        return (default_rate.rate, default_rate.id), None
    return (Decimal("0"), None), None


def _next_invoice_number():
    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    if not settings:
        settings = stamp_tenant(CompanySettings(company_name=g.tenant.name))
        db.session.add(settings)
        db.session.flush()
    number = f"{settings.invoice_prefix}{settings.next_invoice_number}"
    settings.next_invoice_number += 1
    return number


@bp.get("")
@tenant_required
@module_required("ar_ap")
def list_invoices():
    q = scoped_query(Invoice)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    invoices = q.order_by(Invoice.issue_date.desc()).all()
    return jsonify(invoices=[i.to_dict(include_lines=False) for i in invoices])


@bp.get("/<invoice_id>")
@tenant_required
@module_required("ar_ap")
def get_invoice(invoice_id):
    invoice = scoped_query(Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    return jsonify(invoice=invoice.to_dict())


@bp.post("")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def create_invoice():
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    customer = scoped_query(Customer).filter_by(id=customer_id).first() if customer_id else None
    if not customer:
        return jsonify(error="A valid customer_id is required"), 400

    tax_resolved, tax_error = _resolve_tax(data)
    if tax_error:
        return jsonify(error=tax_error), 400
    tax_rate_pct, tax_rate_id = tax_resolved

    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    terms_days = settings.default_invoice_terms_days if settings else 30

    issue_date = _parse_date(data.get("issue_date"), datetime.utcnow().date())
    due_date = _parse_date(data.get("due_date"), issue_date + timedelta(days=terms_days))

    invoice = stamp_tenant(Invoice(
        customer_id=customer.id,
        invoice_number=data.get("invoice_number") or _next_invoice_number(),
        status="draft",
        issue_date=issue_date,
        due_date=due_date,
        memo=data.get("memo"),
        terms=data.get("terms"),
        created_by=g.user_id,
    ))
    _apply_lines(invoice, data.get("lines"))
    invoice.recalculate_totals(tax_rate_pct, tax_rate_id)

    db.session.add(invoice)
    db.session.flush()
    log_action("invoice", invoice.id, "create", {"invoice_number": invoice.invoice_number, "total": str(invoice.total)})
    db.session.commit()
    return jsonify(invoice=invoice.to_dict()), 201


@bp.patch("/<invoice_id>")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def update_invoice(invoice_id):
    invoice = scoped_query(Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    if invoice.status not in ("draft",):
        return jsonify(error=f"Invoice in status '{invoice.status}' cannot be edited"), 409

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("memo", "terms"):
        if field in data:
            setattr(invoice, field, data[field])
            changes[field] = data[field]
    if "issue_date" in data:
        invoice.issue_date = _parse_date(data["issue_date"])
    if "due_date" in data:
        invoice.due_date = _parse_date(data["due_date"])
    if "lines" in data:
        _apply_lines(invoice, data["lines"])
        changes["lines"] = "updated"

    if "tax_rate" in data or "tax_rate_id" in data:
        tax_resolved, tax_error = _resolve_tax(data)
        if tax_error:
            return jsonify(error=tax_error), 400
        tax_rate_pct, tax_rate_id = tax_resolved
    else:
        tax_rate_pct, tax_rate_id = invoice.tax_rate_pct, invoice.tax_rate_id

    invoice.recalculate_totals(tax_rate_pct, tax_rate_id)
    invoice.updated_by = g.user_id
    log_action("invoice", invoice.id, "update", changes)
    db.session.commit()
    return jsonify(invoice=invoice.to_dict())


@bp.post("/<invoice_id>/send")
@tenant_required
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def send_invoice(invoice_id):
    invoice = scoped_query(Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    if invoice.status != "draft":
        return jsonify(error=f"Invoice in status '{invoice.status}' cannot be sent"), 409
    invoice.status = "sent"
    invoice.updated_by = g.user_id
    log_action("invoice", invoice.id, "send")
    db.session.commit()
    return jsonify(invoice=invoice.to_dict())


@bp.post("/<invoice_id>/void")
@tenant_required
@module_required("ar_ap")
@role_required("owner_admin", "accountant")
def void_invoice(invoice_id):
    invoice = scoped_query(Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    invoice.status = "void"
    invoice.balance_due = Decimal("0")
    invoice.updated_by = g.user_id
    log_action("invoice", invoice.id, "void")
    db.session.commit()
    return jsonify(invoice=invoice.to_dict())


@bp.get("/<invoice_id>/pdf")
@tenant_required
@module_required("ar_ap")
def invoice_pdf(invoice_id):
    invoice = scoped_query(Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    pdf_bytes = render_invoice_pdf(invoice, settings)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={invoice.invoice_number}.pdf"},
    )
