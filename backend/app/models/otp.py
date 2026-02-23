"""OTP model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class OTPPurpose(str, enum.Enum):
    """OTP purposes"""
    VERIFICATION = "VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class OTP(Base):
    """OTP database model"""
    __tablename__ = "otps"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(SQLEnum(OTPPurpose), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="otps")
    
    def __repr__(self):
        return f"<OTP(id={self.id}, user_id={self.user_id}, purpose={self.purpose})>"
