from datetime import datetime, date

from flask import Blueprint, request, jsonify, g

from app.middleware.tenant_scope import tenant_required
from app.utils.decorators import role_required, module_required
from app.services import reports as report_service

bp = Blueprint("reports", __name__)

REPORT_ROLES = ("owner_admin", "accountant", "read_only_auditor")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _default_range():
    today = date.today()
    start = today.replace(day=1)
    return start, today


def _resolve_range():
    default_start, default_end = _default_range()
    start = _parse_date(request.args.get("start"), default_start)
    end = _parse_date(request.args.get("end"), default_end)
    return start, end


@bp.get("/profit-loss")
@tenant_required
@module_required("ar_ap")
@role_required(*REPORT_ROLES)
def profit_loss():
    start, end = _resolve_range()
    group_by = request.args.get("group_by", "none")
    if group_by not in ("none", "day", "month"):
        return jsonify(error="group_by must be one of: none, day, month"), 400
    return jsonify(report_service.profit_and_loss(g.tenant_id, start, end, group_by))


@bp.get("/income")
@tenant_required
@module_required("ar_ap")
@role_required(*REPORT_ROLES)
def income():
    start, end = _resolve_range()
    group_by = request.args.get("group_by", "day")
    if group_by not in ("day", "month"):
        return jsonify(error="group_by must be one of: day, month"), 400
    return jsonify(report_service.income_report(g.tenant_id, start, end, group_by))


@bp.get("/sales-tax")
@tenant_required
@module_required("ar_ap")
@role_required(*REPORT_ROLES)
def sales_tax():
    start, end = _resolve_range()
    group_by = request.args.get("group_by", "none")
    if group_by not in ("none", "day", "month"):
        return jsonify(error="group_by must be one of: none, day, month"), 400
    return jsonify(report_service.sales_tax_report(g.tenant_id, start, end, group_by))


@bp.get("/aging-receivables")
@tenant_required
@module_required("ar_ap")
@role_required(*REPORT_ROLES)
def aging_receivables():
    as_of = _parse_date(request.args.get("as_of"), date.today())

    ranges_param = request.args.get("ranges", "30,60,90")
    try:
        ranges = [int(x.strip()) for x in ranges_param.split(",") if x.strip()]
    except ValueError:
        return jsonify(error="ranges must be a comma-separated list of integers, e.g. 30,60,90"), 400
    if not ranges:
        return jsonify(error="ranges must contain at least one bucket edge"), 400

    issue_start = _parse_date(request.args.get("issue_start"))
    issue_end = _parse_date(request.args.get("issue_end"))

    return jsonify(report_service.aging_receivables(g.tenant_id, as_of, ranges, issue_start, issue_end))
