"""Budget-vs-actual rollup for a Project. Computed live from source
records on every call rather than stored/cached -- this codebase has
already been bitten once (see Invoice.refresh_balance) by a cached
relationship going stale the moment a sibling record is inserted in the
same session, so actual cost here is always a fresh aggregate query."""
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models import TimeEntry, WorkOrder, Bill


def budget_vs_actual(project) -> dict:
    labor_hours = db.session.query(func.coalesce(func.sum(TimeEntry.hours), 0)).filter(
        TimeEntry.project_id == project.id
    ).scalar()
    labor_hours = Decimal(labor_hours)

    labor_amount = db.session.query(
        func.coalesce(func.sum(TimeEntry.hours * TimeEntry.hourly_rate), 0)
    ).filter(TimeEntry.project_id == project.id).scalar()
    labor_amount = Decimal(labor_amount).quantize(Decimal("0.01"))

    work_order_amount = db.session.query(func.coalesce(func.sum(WorkOrder.subtotal), 0)).filter(
        WorkOrder.project_id == project.id, WorkOrder.is_deleted == False,  # noqa: E712
    ).scalar()
    work_order_amount = Decimal(work_order_amount)

    bill_amount = db.session.query(func.coalesce(func.sum(Bill.total), 0)).filter(
        Bill.project_id == project.id, Bill.is_deleted == False,  # noqa: E712
        Bill.status != "void",
    ).scalar()
    bill_amount = Decimal(bill_amount)

    actual_amount = (labor_amount + work_order_amount + bill_amount).quantize(Decimal("0.01"))

    return {
        "budget_hours": str(project.budget_hours),
        "actual_hours": str(labor_hours),
        "hours_variance": str(project.budget_hours - labor_hours),
        "budget_amount": str(project.budget_amount),
        "actual_amount": str(actual_amount),
        "amount_variance": str(project.budget_amount - actual_amount),
        "breakdown": {
            "labor_amount": str(labor_amount),
            "work_order_amount": str(work_order_amount),
            "bill_amount": str(bill_amount),
        },
    }
