"""Admin Refresh Token model"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship


class AdminRefreshToken(Base):
    """Admin Refresh Token database model"""

    __tablename__ = "admin_refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    admin = relationship("Admin", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<AdminRefreshToken(id={self.id}, admin_id={self.admin_id}, revoked={self.revoked})>"
