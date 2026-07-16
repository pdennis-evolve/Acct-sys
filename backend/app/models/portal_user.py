from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin

_hasher = PasswordHasher()


class PortalUser(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """Login for one of the TENANT'S customers to use the customer portal
    -- deliberately not a row in the internal `users` table (which is
    staff, with staff roles). A portal token can never authenticate an
    internal endpoint and vice versa; see app/middleware/tenant_scope.py."""

    __tablename__ = "portal_users"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "email", name="uq_portal_users_tenant_email"),
    )

    customer_id: Mapped[str] = mapped_column(db.ForeignKey("customers.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True), nullable=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = _hasher.hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        try:
            return _hasher.verify(self.password_hash, raw_password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
