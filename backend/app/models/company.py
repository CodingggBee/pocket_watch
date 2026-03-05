"""Company model — public schema (one row per tenant)"""
import uuid
from datetime import datetime
from app.database import PublicBase
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship


class Company(PublicBase):
    """Company (tenant) database model — public schema"""

    __tablename__ = "companies"

    company_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Stripe billing
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    payment_methods = relationship("PaymentMethod", back_populates="company", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="company", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")
    company_subscription = relationship("CompanySubscription", back_populates="company", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company(id={self.company_id}, name={self.company_name})>"
