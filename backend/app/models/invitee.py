"""Invitee model"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship


class Invitee(Base):
    """Invitee database model"""

    __tablename__ = "invitees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Invitee fields
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    pin_hash = Column(String(255), nullable=True)  # 4-digit PIN hash
    full_name = Column(String(255), nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    otps = relationship(
        "InviteeOTP", back_populates="invitee", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "InviteeRefreshToken", back_populates="invitee", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Invitee(id={self.id}, phone={self.phone_number})>"
