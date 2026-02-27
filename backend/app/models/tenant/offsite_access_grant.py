"""Offsite access grant — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text


class OffsiteAccessGrant(TenantBase):
    """Grants a user remote (offsite) data-entry access to a plant"""

    __tablename__ = "offsite_access_grants"

    grant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    granted_by = Column(String(36), nullable=False)   # user_id of granting admin/manager
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(36), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<OffsiteAccessGrant(id={self.grant_id}, user={self.user_id}, plant={self.plant_id})>"
