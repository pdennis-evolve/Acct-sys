from decimal import Decimal

from datetime import date
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin

CASH_ACCOUNT_TYPES = ["checking", "savings", "cash", "credit_card"]
CASH_TXN_TYPES = ["deposit", "withdrawal", "payment", "check"]


class CashAccount(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "cash_accounts"

    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(db.String(20), nullable=False, default="checking")
    bank_name: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    account_number_last4: Mapped[str | None] = mapped_column(db.String(4), nullable=True)
    gl_account_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("accounts.id"), nullable=True
    )
    current_balance: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "account_type": self.account_type,
            "bank_name": self.bank_name,
            "account_number_last4": self.account_number_last4,
            "gl_account_id": self.gl_account_id,
            "current_balance": str(self.current_balance),
            "is_active": self.is_active,
        }


class CashTransaction(UUIDPKMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "cash_transactions"

    cash_account_id: Mapped[str] = mapped_column(
        db.ForeignKey("cash_accounts.id"), nullable=False, index=True
    )
    txn_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    txn_type: Mapped[str] = mapped_column(db.String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False)
    payee: Mapped[str | None] = mapped_column(db.String(200), nullable=True)
    memo: Mapped[str | None] = mapped_column(db.String(500), nullable=True)
    check_number: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    related_payment_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("payments.id"), nullable=True
    )
    related_vendor_payment_id: Mapped[str | None] = mapped_column(
        db.ForeignKey("vendor_payments.id"), nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cash_account_id": self.cash_account_id,
            "txn_date": self.txn_date.isoformat() if self.txn_date else None,
            "txn_type": self.txn_type,
            "amount": str(self.amount),
            "payee": self.payee,
            "memo": self.memo,
            "check_number": self.check_number,
            "related_payment_id": self.related_payment_id,
            "related_vendor_payment_id": self.related_vendor_payment_id,
        }
