from pydantic import BaseModel, Field
from typing import Optional

class SaveCardRequest(BaseModel):
    """Request to save a payment method created by Stripe SDK on frontend"""
    payment_method_id: str = Field(..., description="Stripe payment method ID from frontend SDK")
    billing_details: Optional[dict] = Field(None, description="Optional billing details override")


class SaveCardResponse(BaseModel):
    success: bool
    message: str
    payment_method_id: str


class PaymentMethodResponse(BaseModel):
    """Response with payment method details"""
    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    cardholder_name: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    is_default: bool

    class Config:
        from_attributes = True


