"""OTP cache — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, String


class OTPCache(TenantBase):
    """OTP cache for phone verification — stores Argon2 hash (not plain OTP)"""

    __tablename__ = "otp_cache"

    otp_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(20), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(String(50), nullable=False, default="VERIFICATION")
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<OTPCache(id={self.otp_id}, phone={self.phone_number})>"
