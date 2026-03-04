"""Characteristic model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String
import enum


class ChartType(str, enum.Enum):
    I_MR = "I-MR"
    XBAR_R = "Xbar-R"
    P_CHART = "P-Chart"


class Characteristic(TenantBase):
    """SPC characteristic monitored at a station"""

    __tablename__ = "characteristics"

    characteristic_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    characteristic_name = Column(String(255), nullable=False)
    unit_of_measure = Column(String(50), nullable=True)
    target_value = Column(Numeric(15, 6), nullable=True)
    usl = Column(Numeric(15, 6), nullable=True)  # Upper Spec Limit
    lsl = Column(Numeric(15, 6), nullable=True)  # Lower Spec Limit
    ucl = Column(Numeric(15, 6), nullable=True)  # Upper Control Limit
    lcl = Column(Numeric(15, 6), nullable=True)  # Lower Control Limit
    cl = Column(Numeric(15, 6), nullable=True)   # Center Line
    sample_size = Column(Integer, nullable=True)
    check_frequency_minutes = Column(Integer, nullable=True)
    chart_type = Column(SQLEnum(ChartType), nullable=False, default=ChartType.I_MR)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Characteristic(id={self.characteristic_id}, name={self.characteristic_name})>"
