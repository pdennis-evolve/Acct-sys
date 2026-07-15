from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin

ACCOUNT_TYPES = ["asset", "liability", "equity", "income", "expense"]


class Account(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, db.Model):
    """Chart of accounts entry. Per-tenant since charts can diverge per client."""

    __tablename__ = "accounts"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "code", name="uq_accounts_tenant_code"),
    )

    code: Mapped[str] = mapped_column(db.String(20), nullable=False)
    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    type: Mapped[str] = mapped_column(db.String(20), nullable=False)
    subtype: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("accounts.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "subtype": self.subtype,
            "parent_id": self.parent_id,
            "is_active": self.is_active,
        }
