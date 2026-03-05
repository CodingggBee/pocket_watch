"""Feature access control utilities and dependencies"""
from functools import wraps
from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Admin
from app.models.plan import CompanySubscription, PlanType


class FeatureGate:
    """Feature access control for subscription-based features"""
    
    # Feature names
    REALTIME_DASHBOARD = "realtime_dashboard"
    VIRTUAL_COACH = "virtual_coach_access"
    SPC_MONITORING = "spc_monitoring"
    ADMIN_CONTROL = "full_admin_control"
    UNLIMITED_DATA = "unlimited_data_entry"
    
    @staticmethod
    def get_subscription(company_id: str, db: Session) -> CompanySubscription:
        """Get company subscription, create default FREE if doesn't exist"""
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
    
    @staticmethod
    def check_feature_access(
        admin: Admin,
        feature: str,
        db: Session,
    ) -> bool:
        """Check if admin's company has access to a feature"""
        subscription = FeatureGate.get_subscription(admin.company_id, db)
        
        if not subscription.is_active:
            return False
        
        return subscription.can_access_feature(feature)
    
    @staticmethod
    def require_feature(feature: str):
        """
        Dependency factory for requiring specific feature access.
        
        Usage:
        @router.get("/admin-only")
        async def admin_feature(
            admin: Admin = Depends(get_current_admin),
            _: None = Depends(FeatureGate.require_feature(FeatureGate.ADMIN_CONTROL))
        ):
            # This endpoint requires full_admin_control feature
            pass
        """
        def dependency(
            admin: Admin,
            db: Session = Depends(get_db),
        ):
            if not FeatureGate.check_feature_access(admin, feature, db):
                subscription = FeatureGate.get_subscription(admin.company_id, db)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your current plan ({subscription.plan_type.value}) does not have access to this feature. Please upgrade to Premium."
                )
            return None
        
        return dependency
    
    @staticmethod
    def check_station_limit(admin: Admin, db: Session) -> dict:
        """Check station limits for the company"""
        subscription = FeatureGate.get_subscription(admin.company_id, db)
        
        return {
            "current_stations": subscription.stations_count,
            "max_stations": subscription.features.get("stations_limit"),
            "can_add_more": subscription.can_add_station(),
            "plan_type": subscription.plan_type.value,
        }


# Convenience dependency functions
def require_admin_control(
    admin: Admin,
    db: Session = Depends(get_db),
):
    """Require full administrative control feature (Premium only)"""
    return FeatureGate.require_feature(FeatureGate.ADMIN_CONTROL)(admin, db)


def require_unlimited_data(
    admin: Admin,
    db: Session = Depends(get_db),
):
    """Require unlimited data entry feature (Premium only)"""
    return FeatureGate.require_feature(FeatureGate.UNLIMITED_DATA)(admin, db)


def check_station_quota(
    admin: Admin,
    db: Session = Depends(get_db),
) -> dict:
    """Check if company can add more stations"""
    limits = FeatureGate.check_station_limit(admin, db)
    
    if not limits["can_add_more"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Station limit reached. Your {limits['plan_type']} plan allows {limits['max_stations']} station(s). Please upgrade to Premium for unlimited stations."
        )
    
    return limits
