"""Geofence check — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Numeric, String
import enum


class CheckSource(str, enum.Enum):
    APP = "app"
    SERVER = "server"


class GeofenceCheck(TenantBase):
    """Records a geofence validation event for a user at a plant"""

    __tablename__ = "geofence_checks"

    check_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    gps_latitude = Column(Numeric(10, 8), nullable=True)
    gps_longitude = Column(Numeric(11, 8), nullable=True)
    is_within_geofence = Column(Boolean, nullable=False)
    ttl_expires_at = Column(DateTime, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    check_source = Column(SQLEnum(CheckSource), nullable=False, default=CheckSource.APP)

    def __repr__(self):
        return f"<GeofenceCheck(id={self.check_id}, within={self.is_within_geofence})>"
