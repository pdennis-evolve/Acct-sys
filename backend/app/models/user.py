from sqlalchemy.orm import Mapped, mapped_column
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin

_hasher = PasswordHasher()

# Per-tenant roles. Super-admins are a separate, cross-tenant concept
# (see SuperAdmin model) and are never a value in this list.
ROLES = [
    "owner_admin",
    "accountant",
    "sales_ar_clerk",
    "warehouse_inventory",
    "dispatcher",
    "technician",
    "read_only_auditor",
]


class User(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    email: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    role: Mapped[str] = mapped_column(db.String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

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
            "tenant_id": self.tenant_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
        }


class SuperAdmin(UUIDPKMixin, TimestampMixin, db.Model):
    """ETG-only cross-tenant layer: provisioning, licensing, support impersonation."""

    __tablename__ = "super_admins"

    email: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

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
        return {"id": self.id, "email": self.email, "full_name": self.full_name}
