"""Measurement model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String


class Measurement(TenantBase):
    """Individual measurement value within a sample"""

    __tablename__ = "measurements"

    measurement_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sample_id = Column(
        String(36), ForeignKey("samples.sample_id"), nullable=False, index=True
    )
    measurement_value = Column(Numeric(15, 6), nullable=False)
    uom_at_capture = Column(String(50), nullable=True)
    measurement_order = Column(Integer, nullable=False, default=1)
    is_outlier = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Measurement(id={self.measurement_id}, value={self.measurement_value})>"
