from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin

VEHICLE_STATUSES = ["active", "maintenance", "out_of_service"]
VEHICLE_TYPES = ["truck", "van", "trailer", "other"]


class Vehicle(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    __tablename__ = "vehicles"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "unit_number", name="uq_vehicles_tenant_unit_number"),
    )

    unit_number: Mapped[str] = mapped_column(db.String(30), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(db.String(20), nullable=False, default="truck")
    make: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(db.String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(db.Integer, nullable=True)
    vin: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    license_plate: Mapped[str | None] = mapped_column(db.String(20), nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "unit_number": self.unit_number,
            "vehicle_type": self.vehicle_type,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "vin": self.vin,
            "license_plate": self.license_plate,
            "status": self.status,
            "notes": self.notes,
            "is_active": self.is_active,
        }


DRIVER_STATUSES = ["active", "on_leave", "inactive"]


class Driver(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditStampMixin, db.Model):
    """Standalone master-data record, like Vendor/Customer -- a driver
    doesn't necessarily need an app login, so this is deliberately not
    tied to the User table."""

    __tablename__ = "drivers"

    full_name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(db.String(50), nullable=True)
    license_class: Mapped[str | None] = mapped_column(db.String(10), nullable=True)
    license_expiration: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "license_number": self.license_number,
            "license_class": self.license_class,
            "license_expiration": self.license_expiration.isoformat() if self.license_expiration else None,
            "status": self.status,
            "notes": self.notes,
            "is_active": self.is_active,
        }
