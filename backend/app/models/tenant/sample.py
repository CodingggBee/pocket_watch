"""Sample model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
import enum


class Shift(str, enum.Enum):
    SHIFT_1 = "shift_1"
    SHIFT_2 = "shift_2"
    SHIFT_3 = "shift_3"


class AccessMode(str, enum.Enum):
    IN_PLANT = "in_plant"
    OFFSITE_GRANTED = "offsite_granted"


class Sample(TenantBase):
    """SPC data sample — a group of measurements taken at one time"""

    __tablename__ = "samples"

    sample_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    characteristic_id = Column(
        String(36), ForeignKey("characteristics.characteristic_id"), nullable=False, index=True
    )
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    sample_number = Column(Integer, nullable=True)
    sample_datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    shift = Column(SQLEnum(Shift), nullable=True)
    gps_latitude = Column(Numeric(10, 8), nullable=True)
    gps_longitude = Column(Numeric(11, 8), nullable=True)
    geofence_check_id = Column(String(36), nullable=True)
    offsite_grant_id = Column(String(36), nullable=True)
    access_mode = Column(SQLEnum(AccessMode), nullable=False, default=AccessMode.IN_PLANT)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Sample(id={self.sample_id}, station={self.station_id})>"
