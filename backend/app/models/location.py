from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin


class Location(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, db.Model):
    """A warehouse/stockroom/yard -- the unit stock levels are tracked
    against. Every tenant gets a default one seeded on creation."""

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    is_default: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address_line1": self.address_line1,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "is_default": self.is_default,
            "is_active": self.is_active,
        }
