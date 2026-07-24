from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

PROJECT_STATUSES = ["planning", "active", "on_hold", "completed", "cancelled"]
PROJECT_TASK_STATUSES = ["todo", "in_progress", "blocked", "done"]


class Project(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Planning/tracking wrapper around one or more Work Orders and/or its
    own task list, with a budget (hours + dollars) checked against actual
    cost rolled up live from TimeEntry hours, linked WorkOrder subtotals,
    and linked Bill totals -- see app/services/projects.py. Nothing here
    duplicates data that Work Orders/Bills/Invoices already own."""

    __tablename__ = "projects"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "project_number", name="uq_projects_tenant_number"),
    )

    customer_id: Mapped[str | None] = mapped_column(db.ForeignKey("customers.id"), nullable=True, index=True)
    project_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="planning")

    project_manager_id: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)

    start_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)

    budget_hours: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False, default=0)
    budget_amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)

    customer = relationship("Customer", lazy="joined")
    manager = relationship("User", lazy="joined", foreign_keys=[project_manager_id])
    tasks = relationship(
        "ProjectTask", backref="project", cascade="all, delete-orphan",
        order_by="ProjectTask.sort_order", lazy="selectin",
    )

    def to_dict(self, include_tasks=True):
        d = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.display_name if self.customer else None,
            "project_number": self.project_number,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "project_manager_id": self.project_manager_id,
            "project_manager_name": self.manager.full_name if self.manager else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "budget_hours": str(self.budget_hours),
            "budget_amount": str(self.budget_amount),
        }
        if include_tasks:
            d["tasks"] = [t.to_dict() for t in self.tasks]
        return d


class ProjectTask(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "project_tasks"

    project_id: Mapped[str] = mapped_column(db.ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="todo")
    assigned_to: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)
    is_milestone: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    due_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    estimated_hours: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    assignee = relationship("User", lazy="joined", foreign_keys=[assigned_to])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.full_name if self.assignee else None,
            "is_milestone": self.is_milestone,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "estimated_hours": str(self.estimated_hours),
            "sort_order": self.sort_order,
        }
