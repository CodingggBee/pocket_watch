"""Invitee OTP model"""

import enum
import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship


class OTPPurpose(str, enum.Enum):
    """OTP purposes"""

    VERIFICATION = "VERIFICATION"
    PIN_RESET = "PIN_RESET"


class InviteeOTP(Base):
    """Invitee OTP database model"""

    __tablename__ = "invitee_otps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invitee_id = Column(
        String(36), ForeignKey("invitees.id"), nullable=False, index=True
    )
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(SQLEnum(OTPPurpose), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    invitee = relationship("Invitee", back_populates="otps")

    def __repr__(self):
        return f"<InviteeOTP(id={self.id}, invitee_id={self.invitee_id}, purpose={self.purpose})>"
