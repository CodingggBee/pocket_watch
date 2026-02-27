"""AI conversation — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String
import enum


class ConversationAccessMode(str, enum.Enum):
    IN_PLANT = "in_plant"
    OFFSITE_GRANTED = "offsite_granted"


class AIConversation(TenantBase):
    """AI coach conversation session"""

    __tablename__ = "ai_conversations"

    conversation_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    violation_id = Column(
        String(36), ForeignKey("violations.violation_id"), nullable=True, index=True
    )
    context_station_id = Column(String(36), nullable=True)
    context_characteristic_id = Column(String(36), nullable=True)
    geofence_check_id = Column(String(36), nullable=True)
    offsite_grant_id = Column(String(36), nullable=True)
    access_mode = Column(
        SQLEnum(ConversationAccessMode), nullable=False,
        default=ConversationAccessMode.IN_PLANT
    )
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AIConversation(id={self.conversation_id}, user={self.user_id})>"
