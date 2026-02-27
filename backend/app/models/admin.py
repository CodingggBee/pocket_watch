"""Admin model — public schema (company owners)"""
import uuid
from datetime import datetime
from app.database import PublicBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship


class Admin(PublicBase):
    """Admin database model — company owner who signs up via email/password"""

    __tablename__ = "admins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Link to tenant company
    company_id = Column(
        String(36), ForeignKey("companies.company_id"), nullable=True, index=True
    )

    # Auth fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships (public schema)
    company = relationship("Company", foreign_keys=[company_id])
    otps = relationship(
        "AdminOTP", back_populates="admin", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "AdminRefreshToken", back_populates="admin", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Admin(id={self.id}, email={self.email})>"
