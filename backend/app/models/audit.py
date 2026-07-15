from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin


class AuditLog(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """Who/when on financial records. Written by app.services.audit, never edited."""

    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(db.ForeignKey("users.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(db.String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(db.String(20), nullable=False)  # create/update/delete
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "changes": self.changes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
