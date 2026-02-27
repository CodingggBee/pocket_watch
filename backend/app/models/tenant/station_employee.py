"""Station employee assignment — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, String


class StationEmployee(TenantBase):
    """Assigns a user to a station"""

    __tablename__ = "station_employees"

    assignment_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(String(36), nullable=True)  # user_id of assigner

    def __repr__(self):
        return f"<StationEmployee(station={self.station_id}, user={self.user_id})>"
