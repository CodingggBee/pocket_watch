"""Plant model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text


class Plant(TenantBase):
    """Plant / facility — tenant schema"""

    __tablename__ = "plants"

    plant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_name = Column(String(255), nullable=False)
    plant_code = Column(String(50), nullable=True, unique=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    geofence_radius_meters = Column(Integer, default=100, nullable=False)
    timezone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    entitlement_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Plant(id={self.plant_id}, name={self.plant_name})>"
