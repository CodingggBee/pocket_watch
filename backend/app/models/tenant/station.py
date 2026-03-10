"""Station model — tenant schema"""

import enum
import uuid
from datetime import datetime

from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class ShiftConfig(str, enum.Enum):
    ONE = "1x"
    TWO = "2x"
    THREE = "3x"


class OperationalStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BillingState(str, enum.Enum):
    PENDING_BILLING = "pending_billing"
    BILLABLE = "billable"
    NON_BILLABLE = "non_billable"


class Station(TenantBase):
    """SPC measurement station — tenant schema"""

    __tablename__ = "stations"

    station_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(
        String(36), ForeignKey("plants.plant_id"), nullable=False, index=True
    )
    department_id = Column(
        String(36), ForeignKey("departments.department_id"), nullable=True, index=True
    )
    line_id = Column(
        String(36), ForeignKey("production_lines.line_id"), nullable=True, index=True
    )
    station_name = Column(String(255), nullable=False)
    station_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    shift_configuration = Column(
        SQLEnum(ShiftConfig), nullable=False, default=ShiftConfig.ONE
    )
    sampling_frequency_minutes = Column(Integer, nullable=True)
    operational_status = Column(
        SQLEnum(OperationalStatus), nullable=False, default=OperationalStatus.ACTIVE
    )
    billing_state = Column(
        SQLEnum(BillingState), nullable=False, default=BillingState.PENDING_BILLING
    )
    # List of product model UUIDs this station processes (stored as JSON array)
    model_ids = Column(JSONB, nullable=True, default=list)
    data_entry_locked = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Station(id={self.station_id}, name={self.station_name})>"

    def __repr__(self):
        return f"<Station(id={self.station_id}, name={self.station_name})>"
