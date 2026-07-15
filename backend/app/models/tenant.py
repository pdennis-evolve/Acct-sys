from datetime import date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin

# Module keys gate both UI nav and API access. A tenant's `modules` JSON
# blob maps these keys -> bool. Missing key == disabled (fail closed).
ALL_MODULES = [
    "ar_ap",
    "inventory",
    "work_orders",
    "transportation",
    "order_tracking",
    "contract_manager",
    "customer_portal",
]

DEFAULT_MODULES = {m: (m == "ar_ap") for m in ALL_MODULES}

LICENSE_STATUSES = ["trial", "active", "grace_period", "locked", "canceled"]


class Tenant(UUIDPKMixin, TimestampMixin, db.Model):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(100), nullable=False, unique=True, index=True)

    modules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: dict(DEFAULT_MODULES))

    seat_limit: Mapped[int] = mapped_column(db.Integer, nullable=False, default=5)

    license_status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="trial")
    license_start: Mapped[date] = mapped_column(db.Date, nullable=True)
    license_end: Mapped[date] = mapped_column(db.Date, nullable=True)
    grace_period_days: Mapped[int] = mapped_column(db.Integer, nullable=False, default=14)

    # Rate/terms tracked for reference only -- the app never derives
    # pricing logic from this field, per project brief section 5.
    plan_notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def has_module(self, module_key: str) -> bool:
        return bool((self.modules or {}).get(module_key, False))

    def is_read_only(self) -> bool:
        return self.license_status in ("grace_period", "locked")

    def is_locked(self) -> bool:
        return self.license_status == "locked" or not self.is_active

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "modules": self.modules,
            "seat_limit": self.seat_limit,
            "license_status": self.license_status,
            "license_start": self.license_start.isoformat() if self.license_start else None,
            "license_end": self.license_end.isoformat() if self.license_end else None,
            "is_active": self.is_active,
        }
