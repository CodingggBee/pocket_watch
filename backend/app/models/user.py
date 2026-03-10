"""User model"""
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
    
    def __repr__(self):
        if self.role == UserRole.ADMIN:
            return f"<User(id={self.id}, email={self.email}, role=admin)>"
        else:
            return f"<User(id={self.id}, phone={self.phone_number}, role=invitee)>"

