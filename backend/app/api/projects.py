from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, g

from app.extensions import db
from app.models import (
    Project, ProjectTask, TimeEntry, Customer, User, Invoice, InvoiceLine, CompanySettings,
    PROJECT_STATUSES, PROJECT_TASK_STATUSES,
)
from app.middleware.tenant_scope import tenant_required, scoped_query, stamp_tenant
from app.utils.decorators import role_required, module_required
from app.services.audit import log_action
from app.services.projects import budget_vs_actual

bp = Blueprint("projects", __name__)

WRITE_ROLES = ("owner_admin", "project_manager")


def _parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _next_project_number():
    last = scoped_query(Project).order_by(Project.created_at.desc()).first()
    if not last:
        return "PRJ-1001"
    try:
        n = int(last.project_number.split("-")[-1]) + 1
    except (ValueError, IndexError):
        n = 1001
    return f"PRJ-{n}"


@bp.get("")
@tenant_required
@module_required("project_manager")
def list_projects():
    q = scoped_query(Project)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    customer_id = request.args.get("customer_id")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    projects = q.order_by(Project.created_at.desc()).all()
    return jsonify(projects=[p.to_dict(include_tasks=False) for p in projects])


@bp.get("/staff")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def list_staff():
    """Lightweight roster for project-manager/task-assignment dropdowns --
    mirrors work_orders.py's /technicians endpoint so PMs don't need the
    owner_admin-only full /api/users list just to assign work."""
    users = scoped_query(User).filter_by(is_active=True).order_by(User.full_name.asc()).all()
    return jsonify(staff=[{"id": u.id, "full_name": u.full_name, "role": u.role} for u in users])


@bp.get("/<project_id>")
@tenant_required
@module_required("project_manager")
def get_project(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404
    return jsonify(project=project.to_dict())


@bp.post("")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400

    customer_id = data.get("customer_id") or None
    if customer_id and not scoped_query(Customer).filter_by(id=customer_id).first():
        return jsonify(error="customer_id not found"), 400

    project_manager_id = data.get("project_manager_id") or None
    if project_manager_id and not scoped_query(User).filter_by(id=project_manager_id).first():
        return jsonify(error="project_manager_id not found"), 400

    try:
        budget_hours = Decimal(str(data.get("budget_hours", 0)))
        budget_amount = Decimal(str(data.get("budget_amount", 0)))
    except InvalidOperation:
        return jsonify(error="budget_hours and budget_amount must be numeric"), 400

    project = stamp_tenant(Project(
        customer_id=customer_id,
        project_number=data.get("project_number") or _next_project_number(),
        name=name,
        description=data.get("description"),
        status="planning",
        project_manager_id=project_manager_id,
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        budget_hours=budget_hours,
        budget_amount=budget_amount,
        created_by=g.user_id,
    ))
    db.session.add(project)
    db.session.flush()
    log_action("project", project.id, "create", {"name": name})
    db.session.commit()
    return jsonify(project=project.to_dict()), 201


@bp.patch("/<project_id>")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def update_project(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404

    data = request.get_json(silent=True) or {}
    changes = {}
    for field in ("name", "description"):
        if field in data:
            setattr(project, field, data[field])
            changes[field] = data[field]
    if "status" in data:
        if data["status"] not in PROJECT_STATUSES:
            return jsonify(error=f"status must be one of {PROJECT_STATUSES}"), 400
        project.status = data["status"]
        changes["status"] = data["status"]
    if "customer_id" in data:
        customer_id = data["customer_id"] or None
        if customer_id and not scoped_query(Customer).filter_by(id=customer_id).first():
            return jsonify(error="customer_id not found"), 400
        project.customer_id = customer_id
    if "project_manager_id" in data:
        pm_id = data["project_manager_id"] or None
        if pm_id and not scoped_query(User).filter_by(id=pm_id).first():
            return jsonify(error="project_manager_id not found"), 400
        project.project_manager_id = pm_id
    if "start_date" in data:
        project.start_date = _parse_date(data["start_date"])
    if "end_date" in data:
        project.end_date = _parse_date(data["end_date"])
    if "budget_hours" in data:
        try:
            project.budget_hours = Decimal(str(data["budget_hours"]))
        except InvalidOperation:
            return jsonify(error="budget_hours must be numeric"), 400
    if "budget_amount" in data:
        try:
            project.budget_amount = Decimal(str(data["budget_amount"]))
        except InvalidOperation:
            return jsonify(error="budget_amount must be numeric"), 400

    project.updated_by = g.user_id
    log_action("project", project.id, "update", changes)
    db.session.commit()
    return jsonify(project=project.to_dict())


@bp.delete("/<project_id>")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def delete_project(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404
    project.soft_delete(user_id=g.user_id)
    log_action("project", project.id, "delete")
    db.session.commit()
    return jsonify(status="deleted")


@bp.get("/<project_id>/budget")
@tenant_required
@module_required("project_manager")
def get_project_budget(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404
    return jsonify(budget=budget_vs_actual(project))


# --- Tasks ---------------------------------------------------------------

@bp.post("/<project_id>/tasks")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def create_task(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400

    assigned_to = data.get("assigned_to") or None
    if assigned_to and not scoped_query(User).filter_by(id=assigned_to).first():
        return jsonify(error="assigned_to not found"), 400

    try:
        estimated_hours = Decimal(str(data.get("estimated_hours", 0)))
    except InvalidOperation:
        return jsonify(error="estimated_hours must be numeric"), 400

    task = stamp_tenant(ProjectTask(
        project_id=project.id,
        name=name,
        description=data.get("description"),
        status="todo",
        assigned_to=assigned_to,
        is_milestone=bool(data.get("is_milestone")),
        due_date=_parse_date(data.get("due_date")),
        estimated_hours=estimated_hours,
        sort_order=data.get("sort_order", len(project.tasks)),
    ))
    db.session.add(task)
    db.session.commit()
    return jsonify(task=task.to_dict()), 201


@bp.patch("/<project_id>/tasks/<task_id>")
@tenant_required
@module_required("project_manager")
def update_task(project_id, task_id):
    task = ProjectTask.query.filter_by(id=task_id, project_id=project_id, tenant_id=g.tenant_id).first()
    if not task:
        return jsonify(error="Task not found"), 404

    # Any staff user may update status on their own assigned task (mirrors
    # the technician-can-work-their-own-ticket pattern from Work Orders);
    # everything else requires PM/owner.
    is_own_task_status_only = (
        task.assigned_to == g.user_id and set((request.get_json(silent=True) or {}).keys()) <= {"status"}
    )
    if g.role not in WRITE_ROLES and not is_own_task_status_only:
        return jsonify(error="Insufficient role for this action"), 403

    data = request.get_json(silent=True) or {}
    if "status" in data:
        if data["status"] not in PROJECT_TASK_STATUSES:
            return jsonify(error=f"status must be one of {PROJECT_TASK_STATUSES}"), 400
        task.status = data["status"]
    if "name" in data:
        task.name = data["name"]
    if "description" in data:
        task.description = data["description"]
    if "assigned_to" in data:
        assigned_to = data["assigned_to"] or None
        if assigned_to and not scoped_query(User).filter_by(id=assigned_to).first():
            return jsonify(error="assigned_to not found"), 400
        task.assigned_to = assigned_to
    if "is_milestone" in data:
        task.is_milestone = bool(data["is_milestone"])
    if "due_date" in data:
        task.due_date = _parse_date(data["due_date"])
    if "estimated_hours" in data:
        try:
            task.estimated_hours = Decimal(str(data["estimated_hours"]))
        except InvalidOperation:
            return jsonify(error="estimated_hours must be numeric"), 400
    if "sort_order" in data:
        task.sort_order = int(data["sort_order"])

    db.session.commit()
    return jsonify(task=task.to_dict())


@bp.delete("/<project_id>/tasks/<task_id>")
@tenant_required
@module_required("project_manager")
@role_required(*WRITE_ROLES)
def delete_task(project_id, task_id):
    task = ProjectTask.query.filter_by(id=task_id, project_id=project_id, tenant_id=g.tenant_id).first()
    if not task:
        return jsonify(error="Task not found"), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify(status="deleted")


# --- Time entries ----------------------------------------------------------

@bp.get("/<project_id>/time-entries")
@tenant_required
@module_required("project_manager")
def list_time_entries(project_id):
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404
    q = TimeEntry.query.filter_by(project_id=project_id, tenant_id=g.tenant_id)
    if request.args.get("billed") == "false":
        q = q.filter(TimeEntry.invoice_line_id.is_(None))
    entries = q.order_by(TimeEntry.entry_date.desc()).all()
    return jsonify(time_entries=[e.to_dict() for e in entries])


@bp.post("/<project_id>/time-entries")
@tenant_required
@module_required("project_manager")
def create_time_entry(project_id):
    """Any staff user may log their own time; PM/owner may log on behalf
    of another user (e.g. entering a paper timesheet)."""
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or g.user_id
    if user_id != g.user_id and g.role not in WRITE_ROLES:
        return jsonify(error="Insufficient role to log time for another user"), 403
    if not scoped_query(User).filter_by(id=user_id).first():
        return jsonify(error="user_id not found"), 400

    task_id = data.get("task_id") or None
    if task_id and not ProjectTask.query.filter_by(id=task_id, project_id=project_id, tenant_id=g.tenant_id).first():
        return jsonify(error="task_id not found on this project"), 400

    try:
        hours = Decimal(str(data.get("hours", 0)))
        hourly_rate = Decimal(str(data.get("hourly_rate", 0)))
    except InvalidOperation:
        return jsonify(error="hours and hourly_rate must be numeric"), 400
    if hours <= 0:
        return jsonify(error="hours must be greater than 0"), 400

    entry_date = _parse_date(data.get("entry_date"), datetime.utcnow().date())

    entry = stamp_tenant(TimeEntry(
        project_id=project.id,
        task_id=task_id,
        user_id=user_id,
        entry_date=entry_date,
        hours=hours,
        billable=data.get("billable", True),
        hourly_rate=hourly_rate,
        memo=data.get("memo"),
        created_by=g.user_id,
    ))
    db.session.add(entry)
    db.session.commit()
    return jsonify(time_entry=entry.to_dict()), 201


@bp.patch("/<project_id>/time-entries/<entry_id>")
@tenant_required
@module_required("project_manager")
def update_time_entry(project_id, entry_id):
    entry = TimeEntry.query.filter_by(id=entry_id, project_id=project_id, tenant_id=g.tenant_id).first()
    if not entry:
        return jsonify(error="Time entry not found"), 404
    if entry.invoice_line_id:
        return jsonify(error="This time entry has already been billed and cannot be edited"), 409
    if entry.user_id != g.user_id and g.role not in WRITE_ROLES:
        return jsonify(error="Insufficient role to edit another user's time entry"), 403

    data = request.get_json(silent=True) or {}
    if "hours" in data:
        try:
            entry.hours = Decimal(str(data["hours"]))
        except InvalidOperation:
            return jsonify(error="hours must be numeric"), 400
    if "hourly_rate" in data:
        try:
            entry.hourly_rate = Decimal(str(data["hourly_rate"]))
        except InvalidOperation:
            return jsonify(error="hourly_rate must be numeric"), 400
    if "billable" in data:
        entry.billable = bool(data["billable"])
    if "memo" in data:
        entry.memo = data["memo"]
    if "entry_date" in data:
        entry.entry_date = _parse_date(data["entry_date"])
    entry.updated_by = g.user_id
    db.session.commit()
    return jsonify(time_entry=entry.to_dict())


@bp.delete("/<project_id>/time-entries/<entry_id>")
@tenant_required
@module_required("project_manager")
def delete_time_entry(project_id, entry_id):
    entry = TimeEntry.query.filter_by(id=entry_id, project_id=project_id, tenant_id=g.tenant_id).first()
    if not entry:
        return jsonify(error="Time entry not found"), 404
    if entry.invoice_line_id:
        return jsonify(error="This time entry has already been billed and cannot be deleted"), 409
    if entry.user_id != g.user_id and g.role not in WRITE_ROLES:
        return jsonify(error="Insufficient role to delete another user's time entry"), 403
    db.session.delete(entry)
    db.session.commit()
    return jsonify(status="deleted")


@bp.post("/<project_id>/bill-time")
@tenant_required
@module_required("project_manager")
@module_required("ar_ap")
@role_required(*WRITE_ROLES)
def bill_time(project_id):
    """Generates a draft Invoice from selected unbilled, billable
    TimeEntries -- mirrors the WorkOrder/Load convert-to-invoice pattern.
    Each entry is stamped with the resulting invoice_line_id so it can
    never be billed twice."""
    project = scoped_query(Project).filter_by(id=project_id).first()
    if not project:
        return jsonify(error="Project not found"), 404
    if not project.customer_id:
        return jsonify(error="This project has no customer set; assign one before billing time"), 400

    data = request.get_json(silent=True) or {}
    entry_ids = data.get("time_entry_ids") or []
    if not entry_ids:
        return jsonify(error="time_entry_ids is required"), 400

    entries = TimeEntry.query.filter(
        TimeEntry.id.in_(entry_ids), TimeEntry.project_id == project_id, TimeEntry.tenant_id == g.tenant_id,
    ).all()
    if len(entries) != len(set(entry_ids)):
        return jsonify(error="One or more time_entry_ids were not found on this project"), 400
    for e in entries:
        if e.invoice_line_id:
            return jsonify(error=f"Time entry {e.id} has already been billed"), 409
        if not e.billable:
            return jsonify(error=f"Time entry {e.id} is marked non-billable"), 400

    from app.api.invoices import _next_invoice_number

    settings = CompanySettings.query.filter_by(tenant_id=g.tenant_id).first()
    terms_days = settings.default_invoice_terms_days if settings else 30
    today = datetime.utcnow().date()

    invoice = stamp_tenant(Invoice(
        customer_id=project.customer_id,
        invoice_number=_next_invoice_number(),
        status="draft",
        issue_date=today,
        due_date=today + timedelta(days=terms_days),
        memo=f"Time billed from project {project.project_number}",
        created_by=g.user_id,
    ))
    for i, entry in enumerate(entries):
        line = InvoiceLine(
            tenant_id=g.tenant_id,
            description=entry.memo or f"{project.name} - labor ({entry.entry_date.isoformat()})",
            quantity=entry.hours,
            unit_price=entry.hourly_rate,
            amount=entry.amount,
            sort_order=i,
        )
        invoice.lines.append(line)

    invoice.recalculate_totals(Decimal("0"), None)
    db.session.add(invoice)
    db.session.flush()

    for line, entry in zip(invoice.lines, entries):
        entry.invoice_line_id = line.id

    log_action("project", project.id, "bill_time", {"invoice_id": invoice.id, "entry_count": len(entries)})
    db.session.commit()
    return jsonify(invoice=invoice.to_dict()), 201
