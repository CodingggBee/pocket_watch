"""Plant subscription — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
import enum


class Platform(str, enum.Enum):
    APPLE = "apple"
    GOOGLE = "google"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    GRACE_PERIOD = "grace_period"


class PlantSubscription(TenantBase):
    """In-app purchase subscription tied to a plant"""

    __tablename__ = "plant_subscriptions"

    subscription_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    product_id = Column(String(255), nullable=False)
    sku = Column(String(100), default="pw_spc_station_monthly", nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    transaction_id = Column(String(500), nullable=False, unique=True)
    original_transaction_id = Column(String(500), nullable=True)
    purchase_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    receipt_data = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    auto_renew_status = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<PlantSubscription(id={self.subscription_id}, plant={self.plant_id}, status={self.status})>"
