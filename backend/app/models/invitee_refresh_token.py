"""Invitee Refresh Token model"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship


class InviteeRefreshToken(Base):
    """Invitee Refresh Token database model"""

    __tablename__ = "invitee_refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invitee_id = Column(
        String(36), ForeignKey("invitees.id"), nullable=False, index=True
    )
    token_hash = Column(String(255), nullable=False, unique=True)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    invitee = relationship("Invitee", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<InviteeRefreshToken(id={self.id}, invitee_id={self.invitee_id}, revoked={self.revoked})>"
