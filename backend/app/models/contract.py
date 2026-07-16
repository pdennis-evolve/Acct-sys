from datetime import date

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

CONTRACT_STATUSES = ["draft", "active", "expired", "terminated", "renewed"]


class Contract(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Attached to a customer file. Key dates are pre-filled from the
    uploaded document by app/services/contract_extraction.py (heuristic,
    best-effort) and are always user-editable afterward -- extraction
    never gets treated as ground truth."""

    __tablename__ = "contracts"

    customer_id: Mapped[str] = mapped_column(db.ForeignKey("customers.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(db.String(300), nullable=False)
    contract_number: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="draft")

    start_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)

    file_storage_key: Mapped[str | None] = mapped_column(db.String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(db.String(300), nullable=True)
    file_content_type: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(db.Integer, nullable=True)
    dates_auto_extracted: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)

    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    customer = relationship("Customer", lazy="joined")

    def to_dict(self):
        today = date.today()
        is_expired = bool(self.end_date and self.end_date < today and self.status not in ("terminated", "renewed"))
        is_expiring_soon = bool(
            self.end_date and not is_expired
            and self.status == "active"
            and (self.end_date - today).days <= 30
        )
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.display_name if self.customer else None,
            "title": self.title,
            "contract_number": self.contract_number,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "renewal_date": self.renewal_date.isoformat() if self.renewal_date else None,
            "auto_renew": self.auto_renew,
            "file_name": self.file_name,
            "file_content_type": self.file_content_type,
            "file_size": self.file_size,
            "has_file": bool(self.file_storage_key),
            "dates_auto_extracted": self.dates_auto_extracted,
            "notes": self.notes,
            "is_expired": is_expired,
            "is_expiring_soon": is_expiring_soon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
