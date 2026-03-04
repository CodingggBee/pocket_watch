"""Shift model — tenant schema"""
import uuid
from datetime import datetime, time
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, String, Time


class Shift(TenantBase):
    """Work shift for a plant"""

    __tablename__ = "shifts"

    shift_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(
        String(36), ForeignKey("plants.plant_id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    shift_name = Column(String(100), nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Shift(id={self.shift_id}, plant={self.plant_id}, name={self.shift_name})>"
