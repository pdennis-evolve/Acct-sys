from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, AuditStampMixin

# What kind of record a tracking number is attached to. Not a hard FK
# (reference_id points at a row in one of several tables depending on
# reference_type) so this stays a simple polymorphic tag rather than
# three nullable foreign keys.
SHIPMENT_REFERENCE_TYPES = ["purchase_order", "invoice", "load"]

SHIPMENT_STATUSES = ["pending", "in_transit", "out_for_delivery", "delivered", "exception", "unknown"]
SHIPMENT_STATUS_SOURCES = ["manual", "carrier_api"]

CARRIERS = ["ups", "fedex", "usps", "dhl", "other", "unknown"]


class Shipment(UUIDPKMixin, TimestampMixin, TenantScopedMixin, AuditStampMixin, db.Model):
    """A tracking number attached to a PO, invoice, or load. Carrier is
    auto-detected from the tracking number's format at creation time;
    status is manually entered unless/until a real carrier API
    integration is configured for this tenant (see app/services/carrier.py)."""

    __tablename__ = "shipments"

    reference_type: Mapped[str] = mapped_column(db.String(20), nullable=False, index=True)
    reference_id: Mapped[str] = mapped_column(db.String(36), nullable=False, index=True)

    tracking_number: Mapped[str] = mapped_column(db.String(50), nullable=False)
    carrier: Mapped[str] = mapped_column(db.String(20), nullable=False, default="unknown")

    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="pending")
    status_source: Mapped[str] = mapped_column(db.String(20), nullable=False, default="manual")
    status_note: Mapped[str | None] = mapped_column(db.String(500), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        from app.services.carrier import tracking_url

        return {
            "id": self.id,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "tracking_url": tracking_url(self.carrier, self.tracking_number),
            "status": self.status,
            "status_source": self.status_source,
            "status_note": self.status_note,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
