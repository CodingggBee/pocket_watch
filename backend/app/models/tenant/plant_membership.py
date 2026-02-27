"""Plant membership — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String
import enum


class PlantRole(str, enum.Enum):
    PLANT_ADMIN = "plant_admin"
    MANAGER = "manager"
    MEMBER = "member"


class PlantMembership(TenantBase):
    """Plant membership — which user has which role at which plant"""

    __tablename__ = "plant_memberships"

    membership_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    role = Column(SQLEnum(PlantRole), nullable=False, default=PlantRole.MEMBER)
    invited_by = Column(String(36), nullable=True)  # user_id of inviter
    invited_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<PlantMembership(plant={self.plant_id}, user={self.user_id}, role={self.role})>"
