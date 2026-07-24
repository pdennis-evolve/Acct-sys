from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, AuditStampMixin


class TimeEntry(UUIDPKMixin, TimestampMixin, TenantScopedMixin, AuditStampMixin, db.Model):
    """Logged labor against a project (optionally a specific task). Once
    billed (invoice_line_id set) an entry is immutable -- the same
    "billed records don't change" rule already used for Invoice/Payment,
    so a bill-time run can never be double-counted."""

    __tablename__ = "time_entries"

    project_id: Mapped[str] = mapped_column(db.ForeignKey("projects.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(db.ForeignKey("project_tasks.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(db.ForeignKey("users.id"), nullable=False, index=True)

    entry_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    hours: Mapped[Decimal] = mapped_column(db.Numeric(6, 2), nullable=False)
    billable: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    hourly_rate: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False, default=0)
    memo: Mapped[str | None] = mapped_column(db.String(500), nullable=True)

    invoice_line_id: Mapped[str | None] = mapped_column(db.ForeignKey("invoice_lines.id"), nullable=True)

    user = relationship("User", lazy="joined", foreign_keys=[user_id])

    @property
    def amount(self) -> Decimal:
        return (self.hours * self.hourly_rate).quantize(Decimal("0.01"))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "hours": str(self.hours),
            "billable": self.billable,
            "hourly_rate": str(self.hourly_rate),
            "amount": str(self.amount),
            "memo": self.memo,
            "invoice_line_id": self.invoice_line_id,
            "billed": self.invoice_line_id is not None,
        }
