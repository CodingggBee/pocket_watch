"""Alert model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
import enum


class AlertType(str, enum.Enum):
    PUSH_NOTIFICATION = "push_notification"
    EMAIL = "email"
    SMS = "sms"


class Alert(TenantBase):
    """Alert sent when a violation is detected"""

    __tablename__ = "alerts"

    alert_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    violation_id = Column(
        String(36), ForeignKey("violations.violation_id"), nullable=False, index=True
    )
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    recipient_user_id = Column(String(36), nullable=False)
    message_title = Column(String(255), nullable=False)
    message_body = Column(Text, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Alert(id={self.alert_id}, type={self.alert_type})>"
