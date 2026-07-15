import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr, Mapped, mapped_column

from app.extensions import db


def _uuid():
    return str(uuid.uuid4())


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TenantScopedMixin:
    """Every business table carries tenant_id. No exceptions.

    All queries against tenant-scoped models must go through
    app.middleware.tenant_scope helpers so the filter is never
    forgotten at the endpoint layer.
    """

    @declared_attr
    def tenant_id(cls):
        return mapped_column(
            UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True
        )


class SoftDeleteMixin:
    """Financial records are never hard-deleted."""

    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        db.DateTime(timezone=True), nullable=True
    )
    deleted_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )

    def soft_delete(self, user_id=None):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id


class AuditStampMixin:
    """created_by/updated_by on financial records, paired with AuditLog rows."""

    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
