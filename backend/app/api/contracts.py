import uuid
from datetime import datetime, date

from flask import Blueprint, request, jsonify, g, Response

from app.extensions import db
from app.models import Contract, CONTRACT_STATUSES, Customer
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.storage import get_storage_backend
from app.services.contract_extraction import extract_text, extract_key_dates

bp = Blueprint("contracts", __name__)

WRITE_ROLES = ("owner_admin", "accountant", "sales_ar_clerk")
ALLOWED_EXTENSIONS = {"pdf", "docx"}


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@tenant_required
@module_required("contract_manager")
def list_contracts():
    q = scoped_query(Contract)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    contracts = [c.to_dict() for c in q.order_by(Contract.end_date.asc().nullslast()).all()]

    expiring_within_days = request.args.get("expiring_within_days")
    if expiring_within_days:
        try:
            days = int(expiring_within_days)
        except ValueError:
            return jsonify(error="expiring_within_days must be an integer"), 400
        today = date.today()
        contracts = [
            c for c in contracts
            if c["end_date"] and c["status"] == "active"
            and 0 <= (datetime.strptime(c["end_date"], "%Y-%m-%d").date() - today).days <= days
        ]

    return jsonify(contracts=contracts)


@bp.get("/<contract_id>")
@tenant_required
@module_required("contract_manager")
def get_contract(contract_id):
    contract = scoped_query(Contract).filter_by(id=contract_id).first()
    if not contract:
        return jsonify(error="Contract not found"), 404
    return jsonify(contract=contract.to_dict())


@bp.post("")
@tenant_required
@module_required("contract_manager")
@role_required(*WRITE_ROLES)
def create_contract():
    """Accepts multipart/form-data: customer_id, title, contract_number,
    notes, auto_renew, start_date/end_date/renewal_date (optional
    explicit overrides), and an optional file. When a file is provided,
    its text is extracted and scanned for key dates -- any date field
    not explicitly supplied in the form is pre-filled from that scan."""
    form = request.form
    customer_id = form.get("customer_id")
    customer = scoped_query(Customer).filter_by(id=customer_id).first() if customer_id else None
    if not customer:
        return jsonify(error="A valid customer_id is required"), 400

    title = (form.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400

    contract = stamp_tenant(Contract(
        customer_id=customer.id,
        title=title,
        contract_number=form.get("contract_number"),
        status=form.get("status") if form.get("status") in CONTRACT_STATUSES else "draft",
        start_date=_parse_date(form.get("start_date")),
        end_date=_parse_date(form.get("end_date")),
        renewal_date=_parse_date(form.get("renewal_date")),
        auto_renew=form.get("auto_renew") == "true",
        notes=form.get("notes"),
        created_by=g.user_id,
    ))

    upload = request.files.get("file")
    if upload and upload.filename:
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify(error="Only PDF and DOCX files are supported"), 400

        upload.stream.seek(0, 2)
        size = upload.stream.tell()
        upload.stream.seek(0)

        key = f"contracts/{g.tenant_id}/{uuid.uuid4()}.{ext}"
        get_storage_backend().save(key, upload.stream, content_type=upload.content_type)

        contract.file_storage_key = key
        contract.file_name = upload.filename
        contract.file_content_type = upload.content_type
        contract.file_size = size

        try:
            upload.stream.seek(0)
            text = extract_text(upload.stream, upload.filename)
            extracted = extract_key_dates(text)
            any_extracted = False
            for field in ("start_date", "end_date", "renewal_date"):
                if getattr(contract, field) is None and extracted.get(field):
                    setattr(contract, field, _parse_date(extracted[field]))
                    any_extracted = True
            contract.dates_auto_extracted = any_extracted
        except Exception:
            # Extraction is best-effort; a malformed/unusual document
            # should never block the upload itself.
            pass

    db.session.add(contract)
    db.session.flush()
    log_action("contract", contract.id, "create", {"title": title})
    db.session.commit()
    return jsonify(contract=contract.to_dict()), 201


@bp.patch("/<contract_id>")
@tenant_required
@module_required("contract_manager")
@role_required(*WRITE_ROLES)
def update_contract(contract_id):
    contract = scoped_query(Contract).filter_by(id=contract_id).first()
    if not contract:
        return jsonify(error="Contract not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("title", "contract_number", "notes"):
        if field in data:
            setattr(contract, field, data[field])
            changes[field] = data[field]
    if "auto_renew" in data:
        contract.auto_renew = bool(data["auto_renew"])
    if "status" in data:
        if data["status"] not in CONTRACT_STATUSES:
            return jsonify(error="Invalid status"), 400
        contract.status = data["status"]
        changes["status"] = data["status"]
    for field in ("start_date", "end_date", "renewal_date"):
        if field in data:
            setattr(contract, field, _parse_date(data[field]))
            changes[field] = data[field]
            contract.dates_auto_extracted = False

    contract.updated_by = g.user_id
    log_action("contract", contract.id, "update", changes)
    db.session.commit()
    return jsonify(contract=contract.to_dict())


@bp.delete("/<contract_id>")
@tenant_required
@module_required("contract_manager")
@role_required(*WRITE_ROLES)
def delete_contract(contract_id):
    contract = scoped_query(Contract).filter_by(id=contract_id).first()
    if not contract:
        return jsonify(error="Contract not found"), 404
    contract.soft_delete(user_id=g.user_id)
    log_action("contract", contract.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")


@bp.get("/<contract_id>/file")
@tenant_required
@module_required("contract_manager")
def download_contract_file(contract_id):
    contract = scoped_query(Contract).filter_by(id=contract_id).first()
    if not contract:
        return jsonify(error="Contract not found"), 404
    if not contract.file_storage_key:
        return jsonify(error="This contract has no attached file"), 404

    stream = get_storage_backend().open_stream(contract.file_storage_key)
    return Response(
        stream.read(),
        mimetype=contract.file_content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{contract.file_name}"'},
    )
