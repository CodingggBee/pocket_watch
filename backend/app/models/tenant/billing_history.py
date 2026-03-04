"""Billing history — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Numeric, String, Text
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingHistory(TenantBase):
    """Billing transaction record"""

    __tablename__ = "billing_history"

    billing_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(
        String(36), ForeignKey("plant_subscriptions.subscription_id"), nullable=False, index=True
    )
    billing_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus), nullable=False)
    invoice_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<BillingHistory(id={self.billing_id}, amount={self.amount}, status={self.payment_status})>"
