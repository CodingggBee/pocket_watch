"""Admin OTP model — public schema"""
import enum
import uuid
from datetime import datetime
from app.database import PublicBase
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship


class OTPPurpose(str, enum.Enum):
    VERIFICATION = "VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class AdminOTP(PublicBase):
    """Admin OTP — public schema"""

    __tablename__ = "admin_otps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(SQLEnum(OTPPurpose), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    admin = relationship("Admin", back_populates="otps")

    def __repr__(self):
        return f"<AdminOTP(id={self.id}, admin_id={self.admin_id}, purpose={self.purpose})>"
