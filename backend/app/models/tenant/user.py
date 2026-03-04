"""User model — tenant schema (plant workers / invitees)"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String


class User(TenantBase):
    """User (plant worker) — lives in the per-company tenant schema"""

    __tablename__ = "users"

    user_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    phone_country_code = Column(String(5), nullable=True)
    
    # Name fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    
    email = Column(String(255), nullable=True, index=True)

    # Default shift assignment
    default_shift_id = Column(String(36), ForeignKey("shifts.shift_id"), nullable=True, index=True)

    # Auth
    pin_hash = Column(String(255), nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<User(id={self.user_id}, phone={self.phone_number})>"
