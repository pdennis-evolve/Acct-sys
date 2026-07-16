from flask import Blueprint, request, jsonify, g

from app.models import Invoice, WorkOrder, Load, Shipment
from app.middleware.tenant_scope import portal_required, portal_scoped_query

bp = Blueprint("portal", __name__)


@bp.get("/invoices")
@portal_required
def list_invoices():
    q = portal_scoped_query(Invoice).filter(Invoice.status != "draft")
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    invoices = q.order_by(Invoice.issue_date.desc()).all()
    return jsonify(invoices=[i.to_dict(include_lines=False) for i in invoices])


@bp.get("/invoices/<invoice_id>")
@portal_required
def get_invoice(invoice_id):
    invoice = portal_scoped_query(Invoice).filter_by(id=invoice_id).filter(Invoice.status != "draft").first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    return jsonify(invoice=invoice.to_dict())


@bp.get("/invoices/<invoice_id>/pdf")
@portal_required
def invoice_pdf(invoice_id):
    from flask import Response
    from app.models import CompanySettings
    from app.services.pdf import render_invoice_pdf

    invoice = portal_scoped_query(Invoice).filter_by(id=invoice_id).filter(Invoice.status != "draft").first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    pdf_bytes = render_invoice_pdf(invoice, settings)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={invoice.invoice_number}.pdf"},
    )


@bp.post("/invoices/<invoice_id>/pay")
@portal_required
def pay_invoice(invoice_id):
    """Honest stub: no Authorize.net (or any other gateway) credentials
    exist for any tenant in this environment. This must never fabricate a
    successful charge or create a Payment record -- it reports plainly
    that online payment isn't wired up yet, same pattern as the Phase 6
    carrier-poll and Phase 7 S3-storage stubs."""
    invoice = portal_scoped_query(Invoice).filter_by(id=invoice_id).filter(Invoice.status != "draft").first()
    if not invoice:
        return jsonify(error="Invoice not found"), 404
    if invoice.balance_due <= 0:
        return jsonify(error="This invoice has no balance due"), 400

    return jsonify(
        error="Online payment isn't connected yet for this account. "
              "A payment gateway (e.g. Authorize.net) has not been configured for this tenant. "
              "Please contact us directly to pay this invoice.",
        payment_processed=False,
    ), 501


@bp.get("/work-orders")
@portal_required
def list_work_orders():
    q = portal_scoped_query(WorkOrder).filter(WorkOrder.status != "draft")
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    work_orders = q.order_by(WorkOrder.created_at.desc()).all()
    return jsonify(work_orders=[_work_order_portal_dict(w, include_lines=False) for w in work_orders])


@bp.get("/work-orders/<work_order_id>")
@portal_required
def get_work_order(work_order_id):
    wo = portal_scoped_query(WorkOrder).filter_by(id=work_order_id).filter(WorkOrder.status != "draft").first()
    if not wo:
        return jsonify(error="Work order not found"), 404
    return jsonify(work_order=_work_order_portal_dict(wo, include_lines=True))


def _work_order_portal_dict(wo, include_lines):
    """Customer-safe view: status/schedule/description only. Internal
    cost breakdown (unit_price, account_id) is never exposed here --
    lines only surface description + quantity so a customer can see what
    was done without seeing our labor/parts pricing structure."""
    d = {
        "id": wo.id,
        "wo_number": wo.wo_number,
        "status": wo.status,
        "problem_description": wo.problem_description,
        "scheduled_date": wo.scheduled_date.isoformat() if wo.scheduled_date else None,
        "completed_at": wo.completed_at.isoformat() if wo.completed_at else None,
        "converted_invoice_id": wo.converted_invoice_id,
    }
    if include_lines:
        d["lines"] = [{"description": l.description, "quantity": str(l.quantity)} for l in wo.lines]
    return d


@bp.get("/tracking")
@portal_required
def list_tracking():
    """Shipments tied to this customer's own invoices or loads only --
    purchase_order-referenced shipments are vendor/internal-side and are
    never exposed here."""
    invoice_ids = [row.id for row in portal_scoped_query(Invoice).with_entities(Invoice.id).all()]
    load_ids = [row.id for row in portal_scoped_query(Load).with_entities(Load.id).all()]

    shipments = []
    if invoice_ids:
        shipments += Shipment.query.filter_by(
            tenant_id=g.tenant_id, reference_type="invoice"
        ).filter(Shipment.reference_id.in_(invoice_ids)).all()
    if load_ids:
        shipments += Shipment.query.filter_by(
            tenant_id=g.tenant_id, reference_type="load"
        ).filter(Shipment.reference_id.in_(load_ids)).all()

    shipments.sort(key=lambda s: s.created_at, reverse=True)
    return jsonify(shipments=[s.to_dict() for s in shipments])
