"""Plan and Subscription models for company billing"""
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import PublicBase


class PlanType(str, enum.Enum):
    """Available subscription plans"""
    FREE = "free"
    PREMIUM = "premium"


class PlanFeatures:
    """Feature definitions for each plan"""
    
    FREE_FEATURES = {
        "stations_limit": 1,  # One station only
        "realtime_dashboard": True,
        "virtual_coach_access": True,
        "spc_monitoring": True,
        "full_admin_control": False,
        "unlimited_data_entry": False,
    }
    
    PREMIUM_FEATURES = {
        "stations_limit": None,  # Unlimited stations
        "realtime_dashboard": True,
        "virtual_coach_access": True,
        "spc_monitoring": True,
        "full_admin_control": True,
        "unlimited_data_entry": True,
    }
    
    @classmethod
    def get_features(cls, plan_type: PlanType) -> dict:
        """Get feature set for a given plan type"""
        if plan_type == PlanType.FREE:
            return cls.FREE_FEATURES
        elif plan_type == PlanType.PREMIUM:
            return cls.PREMIUM_FEATURES
        return {}


class CompanySubscription(PublicBase):
    """Company subscription/plan information"""
    __tablename__ = "company_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(36), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Plan details
    plan_type = Column(SQLEnum(PlanType), nullable=False, default=PlanType.FREE)
    stations_count = Column(Integer, default=1, nullable=False)  # Number of active stations
    
    # Billing
    monthly_cost = Column(Integer, default=0)  # In cents, $0 for free, $9900 per station for premium
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    trial_ends_at = Column(DateTime, nullable=True)  # For future trial functionality
    
    # Timestamps
    plan_started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="company_subscription")
    
    def __repr__(self):
        return f"<CompanySubscription(company_id={self.company_id}, plan={self.plan_type}, stations={self.stations_count})>"
    
    @property
    def features(self) -> dict:
        """Get available features for this subscription"""
        return PlanFeatures.get_features(self.plan_type)
    
    def can_access_feature(self, feature: str) -> bool:
        """Check if this subscription can access a specific feature"""
        return self.features.get(feature, False)
    
    def can_add_station(self) -> bool:
        """Check if company can add more stations"""
        if self.plan_type == PlanType.FREE:
            return self.stations_count < 1
        # Premium has unlimited stations
        return True
    
    def calculate_monthly_cost(self) -> int:
        """Calculate monthly cost in cents"""
        if self.plan_type == PlanType.FREE:
            return 0
        elif self.plan_type == PlanType.PREMIUM:
            return 9900 * self.stations_count  # $99.00 per station
        return 0
