"""User session model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class UserSession(TenantBase):
    """User JWT session — tenant schema"""

    __tablename__ = "user_sessions"

    session_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    jwt_token_hash = Column(Text, nullable=True)
    refresh_token_hash = Column(Text, nullable=False)
    device_info = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserSession(id={self.session_id}, user_id={self.user_id})>"
