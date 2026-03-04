"""Subscription webhook — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
import enum


class WebhookPlatform(str, enum.Enum):
    APPLE = "apple"
    GOOGLE = "google"


class SubscriptionWebhook(TenantBase):
    """Raw App Store / Play Store server notification"""

    __tablename__ = "subscription_webhooks"

    webhook_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=True, index=True)
    subscription_id = Column(
        String(36), ForeignKey("plant_subscriptions.subscription_id"), nullable=True, index=True
    )
    platform = Column(SQLEnum(WebhookPlatform), nullable=False)
    notification_type = Column(String(100), nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SubscriptionWebhook(id={self.webhook_id}, type={self.notification_type})>"
