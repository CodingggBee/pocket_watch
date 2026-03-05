"""
⚠️ DEPRECATED - DO NOT USE ⚠️

This file contains the OLD unified User model that was replaced in migration b2c3d4e5f6g7.

CURRENT ARCHITECTURE (Multi-tenant):
- Public schema: `admins` table (managed by Admin model)
- Tenant schemas: `users` table (managed by tenant.User model)

This file is kept for reference only. Use:
- app.models.admin.Admin for public schema admin users
- app.models.tenant.user.User for tenant schema plant workers

Payment functionality should use Company-level billing (not individual users).
"""
# User model (DEPRECATED - see note above)
import enum
import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import relationship


class UserRole(str, enum.Enum):
    """User roles"""
    ADMIN = "admin"
    INVITEE = "invitee"


class User(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Add relationships to payment tables
    payment_methods = relationship(
        "PaymentMethod",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Common fields
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.INVITEE)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Admin-specific fields (email/password)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verified for admins
    
    # Invitee-specific fields (phone/PIN)
    phone_number = Column(String(20), unique=True, nullable=True, index=True)
    pin_hash = Column(String(255), nullable=True)  # 4-digit PIN hash
    phone_verified = Column(Boolean, default=False, nullable=False)  # Phone verified for invitees
    
    # Relationships
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    # Stripe
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    payment_methods = relationship("PaymentMethod", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        if self.role == UserRole.ADMIN:
            return f"<User(id={self.id}, email={self.email}, role=admin)>"
        else:
            return f"<User(id={self.id}, phone={self.phone_number}, role=invitee)>"

