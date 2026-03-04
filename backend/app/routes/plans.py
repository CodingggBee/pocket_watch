"""Plan/Subscription routes for company plan management"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.admin import Admin
from app.models.company import Company
from app.models.plan import CompanySubscription, PlanType, PlanFeatures
from app.schemas.plan import (
    SelectPlanRequest,
    UpdateStationsRequest,
    SubscriptionResponse,
    PlanDetailsResponse,
    PlanFeaturesResponse,
    AvailablePlansResponse,
    FeatureAccessResponse,
    PlanTypeEnum,
)
from app.utils.jwt import verify_access_token

router = APIRouter(prefix="/admin/plans", tags=["Plans & Subscriptions"])
bearer_scheme = HTTPBearer()


# ========================================
# DEPENDENCY: Get current admin
# ========================================

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    """Validates Bearer token and returns the Admin object."""
    token = credentials.credentials
    admin_id = verify_access_token(token)
    
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found"
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive"
        )
    if not admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin not associated with a company"
        )
    return admin


# ========================================
# HELPER FUNCTIONS
# ========================================

def format_price_usd(cents: int) -> str:
    """Format price in cents to USD string"""
    dollars = cents / 100
    return f"${dollars:.2f}"


def get_or_create_subscription(company_id: str, db: Session) -> CompanySubscription:
    """Get or create subscription for a company (defaults to FREE plan)"""
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.company_id == company_id
    ).first()
    
    if not subscription:
        # Create default FREE subscription
        subscription = CompanySubscription(
            company_id=company_id,
            plan_type=PlanType.FREE,
            stations_count=1,
            monthly_cost=0,
            is_active=True,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription


# ========================================
# PLAN ENDPOINTS
# ========================================

@router.get("/available", response_model=AvailablePlansResponse)
async def get_available_plans(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get list of all available subscription plans with features and pricing.
    """
    plans = [
        PlanDetailsResponse(
            plan_type=PlanTypeEnum.FREE,
            name="Free Plan",
            description="Access to all features for one station to experience the power of PocketWatch process control.",
            price_per_station=0,
            features=PlanFeaturesResponse(**PlanFeatures.FREE_FEATURES),
        ),
        PlanDetailsResponse(
            plan_type=PlanTypeEnum.PREMIUM,
            name="Premium Plan",
            description="Unlock full administrative control over the number of stations and users at your location",
            price_per_station=9900,  # $99.00 in cents
            features=PlanFeaturesResponse(**PlanFeatures.PREMIUM_FEATURES),
        ),
    ]
    
    return AvailablePlansResponse(plans=plans)


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get the company's current subscription details.
    """
    subscription = get_or_create_subscription(current_admin.company_id, db)
    
    return SubscriptionResponse(
        id=str(subscription.id),
        company_id=subscription.company_id,
        plan_type=PlanTypeEnum(subscription.plan_type.value),
        stations_count=subscription.stations_count,
        monthly_cost=subscription.monthly_cost,
        monthly_cost_usd=format_price_usd(subscription.monthly_cost),
        is_active=subscription.is_active,
        features=PlanFeaturesResponse(**subscription.features),
        plan_started_at=subscription.plan_started_at,
        created_at=subscription.created_at,
    )


@router.post("/select", response_model=SubscriptionResponse)
async def select_plan(
    request: SelectPlanRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Select or change the company's subscription plan.
    
    - FREE plan: Limited to 1 station, no payment required
    - PREMIUM plan: Requires payment method, charged per station per month
    """
    try:
        # Get company
        company = db.query(Company).filter(Company.company_id == current_admin.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get or create subscription
        subscription = get_or_create_subscription(current_admin.company_id, db)
        
        # Validate plan downgrade/upgrade
        if request.plan_type == PlanTypeEnum.FREE:
            # Downgrading to free - limit to 1 station
            if subscription.stations_count > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot downgrade to free plan with more than 1 station. Please reduce stations first."
                )
            new_stations = 1
        else:
            # Upgrading to premium
            new_stations = request.stations_count
            
            # Check if payment method exists for premium plan
            if not company.stripe_customer_id:
                raise HTTPException(
                    status_code=400,
                    detail="Premium plan requires a payment method. Please add a payment method first."
                )
        
        # Update subscription
        old_plan = subscription.plan_type
        subscription.plan_type = PlanType(request.plan_type.value)
        subscription.stations_count = new_stations
        subscription.monthly_cost = subscription.calculate_monthly_cost()
        subscription.is_active = True
        
        # Update plan start date if changing plans
        if old_plan != subscription.plan_type:
            subscription.plan_started_at = datetime.utcnow()
        
        db.commit()
        db.refresh(subscription)
        
        return SubscriptionResponse(
            id=str(subscription.id),
            company_id=subscription.company_id,
            plan_type=PlanTypeEnum(subscription.plan_type.value),
            stations_count=subscription.stations_count,
            monthly_cost=subscription.monthly_cost,
            monthly_cost_usd=format_price_usd(subscription.monthly_cost),
            is_active=subscription.is_active,
            features=PlanFeaturesResponse(**subscription.features),
            plan_started_at=subscription.plan_started_at,
            created_at=subscription.created_at,
        )
    
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")


@router.put("/stations", response_model=SubscriptionResponse)
async def update_stations(
    request: UpdateStationsRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Update the number of stations (Premium plan only).
    
    Cost will be recalculated based on new station count.
    """
    try:
        subscription = get_or_create_subscription(current_admin.company_id, db)
        
        # Validate premium plan
        if subscription.plan_type != PlanType.PREMIUM:
            raise HTTPException(
                status_code=403,
                detail="Station count can only be modified on Premium plan. Please upgrade first."
            )
        
        # Update stations
        subscription.stations_count = request.stations_count
        subscription.monthly_cost = subscription.calculate_monthly_cost()
        
        db.commit()
        db.refresh(subscription)
        
        return SubscriptionResponse(
            id=str(subscription.id),
            company_id=subscription.company_id,
            plan_type=PlanTypeEnum(subscription.plan_type.value),
            stations_count=subscription.stations_count,
            monthly_cost=subscription.monthly_cost,
            monthly_cost_usd=format_price_usd(subscription.monthly_cost),
            is_active=subscription.is_active,
            features=PlanFeaturesResponse(**subscription.features),
            plan_started_at=subscription.plan_started_at,
            created_at=subscription.created_at,
        )
    
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to update stations: {str(e)}")


@router.get("/features/{feature_name}", response_model=FeatureAccessResponse)
async def check_feature_access(
    feature_name: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Check if the company's current plan has access to a specific feature.
    
    Available features:
    - realtime_dashboard
    - virtual_coach_access
    - spc_monitoring
    - full_admin_control
    - unlimited_data_entry
    """
    subscription = get_or_create_subscription(current_admin.company_id, db)
    
    has_access = subscription.can_access_feature(feature_name)
    
    message = None
    if not has_access:
        message = f"This feature requires an upgrade to Premium plan."
    
    return FeatureAccessResponse(
        has_access=has_access,
        feature=feature_name,
        current_plan=PlanTypeEnum(subscription.plan_type.value),
        message=message,
    )
