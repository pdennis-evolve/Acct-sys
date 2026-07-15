from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import CompanySettings
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required

bp = Blueprint("settings", __name__)


@bp.get("")
@tenant_required
def get_settings():
    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    if not settings:
        settings = stamp_tenant(CompanySettings(company_name=g.tenant.name))
        db.session.add(settings)
        db.session.commit()
    return jsonify(settings=settings.to_dict())


@bp.patch("")
@tenant_required
@role_required("owner_admin")
def update_settings():
    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    if not settings:
        settings = stamp_tenant(CompanySettings(company_name=g.tenant.name))
        db.session.add(settings)

    data = request.get_json(silent=True) or {}
    fields = [
        "company_name", "address_line1", "address_line2", "city", "state",
        "postal_code", "country", "phone", "email", "logo_url",
        "fiscal_year_start_month", "invoice_prefix", "next_invoice_number",
        "default_invoice_terms_days",
    ]
    for f in fields:
        if f in data:
            setattr(settings, f, data[f])

    db.session.commit()
    return jsonify(settings=settings.to_dict())
