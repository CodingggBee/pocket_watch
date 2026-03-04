"""Plan/Subscription schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PlanTypeEnum(str, Enum):
    """Plan types available"""
    FREE = "free"
    PREMIUM = "premium"


class PlanFeaturesResponse(BaseModel):
    """Features available in a plan"""
    stations_limit: Optional[int] = Field(None, description="Maximum number of stations (None = unlimited)")
    realtime_dashboard: bool = Field(..., description="Access to realtime dashboard views")
    virtual_coach_access: bool = Field(..., description="24/7 Access to Virtual Coach")
    spc_monitoring: bool = Field(..., description="Continuous SPC Monitoring")
    full_admin_control: bool = Field(..., description="Full administrative control")
    unlimited_data_entry: bool = Field(..., description="Unlimited data entry capability")


class PlanDetailsResponse(BaseModel):
    """Details about a specific plan"""
    plan_type: PlanTypeEnum
    name: str
    description: str
    price_per_station: int = Field(..., description="Price per station in cents per month")
    features: PlanFeaturesResponse


class SelectPlanRequest(BaseModel):
    """Request to select/change subscription plan"""
    plan_type: PlanTypeEnum = Field(..., description="Plan to activate")
    stations_count: int = Field(1, ge=1, description="Number of stations (ignored for free plan)")


class UpdateStationsRequest(BaseModel):
    """Request to update number of stations (Premium only)"""
    stations_count: int = Field(..., ge=1, description="New number of stations")


class SubscriptionResponse(BaseModel):
    """Current subscription details"""
    id: str
    company_id: str
    plan_type: PlanTypeEnum
    stations_count: int
    monthly_cost: int = Field(..., description="Monthly cost in cents")
    monthly_cost_usd: str = Field(..., description="Monthly cost in USD (formatted)")
    is_active: bool
    features: PlanFeaturesResponse
    plan_started_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeatureAccessResponse(BaseModel):
    """Response for feature access check"""
    has_access: bool
    feature: str
    current_plan: PlanTypeEnum
    message: Optional[str] = None


class AvailablePlansResponse(BaseModel):
    """List of all available plans"""
    plans: list[PlanDetailsResponse]
