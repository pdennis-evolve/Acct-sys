from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin

EMAIL_PROVIDERS = ["microsoft", "google"]


class EmailConnection(UUIDPKMixin, TimestampMixin, TenantScopedMixin, db.Model):
    """One connected mailbox per (tenant, user, provider) -- invoices send
    as this user's own O365/Gmail account via Graph/Gmail API, never a
    shared SMTP relay. Tokens are only ever populated by a real OAuth
    code exchange (see app/services/email_oauth.py); nothing here is
    fabricated when a provider isn't configured for this environment."""

    __tablename__ = "email_connections"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "user_id", "provider", name="uq_email_connections_tenant_user_provider"),
    )

    user_id: Mapped[str] = mapped_column(db.ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(db.String(20), nullable=False)
    email_address: Mapped[str] = mapped_column(db.String(255), nullable=False)

    access_token: Mapped[str] = mapped_column(db.Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    token_expires_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)

    connected_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "email_address": self.email_address,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
        }
