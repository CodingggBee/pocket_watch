"""Payment models — public schema (company-level billing)"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import PublicBase


class PaymentMethod(PublicBase):
    """Payment method for a company (Stripe)"""
    __tablename__ = "payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(36), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Stripe fields
    stripe_payment_method_id = Column(String(255), unique=True, nullable=False, index=True)
    brand = Column(String(50))  # visa, mastercard, amex, etc.
    last4 = Column(String(4))
    exp_month = Column(Integer)
    exp_year = Column(Integer)
    
    # Billing details
    cardholder_name = Column(String(255))
    billing_postal_code = Column(String(20))
    billing_country = Column(String(2))  # 2-letter country code
    
    # Metadata
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="payment_methods")

    def __repr__(self):
        return f"<PaymentMethod {self.brand} ****{self.last4}>"


class Transaction(PublicBase):
    """Transaction for a company (Stripe)"""
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(36), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Stripe fields
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    
    # Payment details
    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(3), default="usd")
    status = Column(String(50), default="pending")  # pending, succeeded, failed, canceled
    description = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.id} - ${self.amount/100:.2f} {self.status}>"


class Subscription(PublicBase):
    """Subscription for a company (Stripe)"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(String(36), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Stripe fields
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_price_id = Column(String(255))
    
    # Subscription details
    status = Column(String(50))  # active, past_due, canceled, incomplete, etc.
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    canceled_at = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription {self.id} - {self.status}>"