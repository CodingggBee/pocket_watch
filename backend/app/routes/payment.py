"""Payment routes — Company-level billing (Admins only)"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import stripe
import os
from datetime import datetime

from app.database import get_db
from app.models.admin import Admin
from app.models.company import Company
from app.models.payment import PaymentMethod
from app.schemas.payment import (
    SaveCardRequest,
    SaveCardResponse,
    PaymentMethodResponse,
)
from app.utils.jwt import verify_access_token

router = APIRouter(prefix="/admin/payment", tags=["Admin Payment"])
bearer_scheme = HTTPBearer()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


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
# HELPER FUNCTION
# ========================================

async def get_or_create_stripe_customer(company: Company, db: Session) -> Company:
    """Get or create Stripe customer for company."""
    if company.stripe_customer_id:
        return company

    # Create new customer
    customer = stripe.Customer.create(
        name=company.company_name,
        metadata={"company_id": company.company_id},
    )

    # Save to database
    company.stripe_customer_id = customer.id
    db.commit()
    db.refresh(company)

    return company


# ========================================
# PAYMENT ENDPOINTS
# ========================================

@router.post("/save-card", response_model=SaveCardResponse)
async def save_card(
    request: SaveCardRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Save a payment method to the company's account.
    
    The payment method ID comes from Stripe frontend SDK (React Native).
    Frontend creates payment method using Stripe SDK, then sends the ID here.
    """
    try:
        # Get company
        company = db.query(Company).filter(Company.company_id == current_admin.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Get or create Stripe customer
        company = await get_or_create_stripe_customer(company, db)

        # Retrieve payment method details from Stripe
        payment_method = stripe.PaymentMethod.retrieve(request.payment_method_id)

        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            request.payment_method_id,
            customer=company.stripe_customer_id,
        )

        # Set as default payment method if requested
        set_as_default = request.billing_details.get("set_as_default", True) if request.billing_details else True
        
        if set_as_default:
            stripe.Customer.modify(
                company.stripe_customer_id,
                invoice_settings={"default_payment_method": request.payment_method_id},
            )

        # Save to database
        db_payment_method = PaymentMethod(
            company_id=company.company_id,
            stripe_payment_method_id=request.payment_method_id,
            brand=payment_method.card.brand,
            last4=payment_method.card.last4,
            exp_month=payment_method.card.exp_month,
            exp_year=payment_method.card.exp_year,
            cardholder_name=payment_method.billing_details.name,
            billing_postal_code=payment_method.billing_details.address.postal_code if payment_method.billing_details.address else None,
            billing_country=payment_method.billing_details.address.country if payment_method.billing_details.address else None,
            is_default=set_as_default,
        )

        # Set other cards as non-default if this is the new default
        if set_as_default:
            db.query(PaymentMethod).filter(
                PaymentMethod.company_id == company.company_id,
                PaymentMethod.stripe_payment_method_id != request.payment_method_id,
            ).update({"is_default": False})

        db.add(db_payment_method)
        db.commit()
        db.refresh(db_payment_method)

        return SaveCardResponse(
            success=True,
            message="Card saved successfully",
            payment_method_id=request.payment_method_id,
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save card: {str(e)}")


@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
async def get_payment_methods(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get all saved payment methods for the company.
    """
    payment_methods = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.company_id == current_admin.company_id)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
        .all()
    )

    return [
        PaymentMethodResponse(
            id=pm.stripe_payment_method_id,
            brand=pm.brand,
            last4=pm.last4,
            exp_month=pm.exp_month,
            exp_year=pm.exp_year,
            cardholder_name=pm.cardholder_name,
            billing_postal_code=pm.billing_postal_code,
            billing_country=pm.billing_country,
            is_default=pm.is_default,
        )
        for pm in payment_methods
    ]


@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a payment method from the company.
    """
    try:
        # Verify ownership
        pm = (
            db.query(PaymentMethod)
            .filter(
                PaymentMethod.stripe_payment_method_id == payment_method_id,
                PaymentMethod.company_id == current_admin.company_id,
            )
            .first()
        )

        if not pm:
            raise HTTPException(status_code=404, detail="Payment method not found")

        # Detach from Stripe
        stripe.PaymentMethod.detach(payment_method_id)

        # Delete from database
        db.delete(pm)
        db.commit()

        return {"success": True, "message": "Payment method removed"}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete payment method: {str(e)}")