"""Station check-in — tenant schema"""

import enum
import uuid
from datetime import datetime

from app.database import TenantBase
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String


class CheckInStatus(str, enum.Enum):
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


class StationCheckIn(TenantBase):
    """Records an employee check-in/check-out event at a station"""

    __tablename__ = "station_checkins"

    checkin_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.user_id"), nullable=False, index=True
    )
    status = Column(
        SQLEnum(CheckInStatus), nullable=False, default=CheckInStatus.CHECKED_IN
    )
    checked_in_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    checked_out_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StationCheckIn(station={self.station_id}, user={self.user_id}, status={self.status})>"

    def __repr__(self):
        return f"<StationCheckIn(station={self.station_id}, user={self.user_id}, status={self.status})>"
