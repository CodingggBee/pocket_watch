"""Violation model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
import enum


class ViolationType(str, enum.Enum):
    NOT_IN_CONTROL = "not_in_control"
    NOT_CAPABLE = "not_capable"
    OUT_OF_SPEC = "out_of_spec"
    MISSING_CHECK = "missing_check"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLOSED = "closed"


class Violation(TenantBase):
    """SPC violation / non-conformance event"""

    __tablename__ = "violations"

    violation_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sample_id = Column(String(36), ForeignKey("samples.sample_id"), nullable=True, index=True)
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    characteristic_id = Column(
        String(36), ForeignKey("characteristics.characteristic_id"), nullable=False, index=True
    )
    violation_type = Column(SQLEnum(ViolationType), nullable=False)
    western_electric_rule = Column(String(50), nullable=True)
    severity = Column(SQLEnum(Severity), nullable=False, default=Severity.MEDIUM)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(ViolationStatus), nullable=False, default=ViolationStatus.OPEN)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(36), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Violation(id={self.violation_id}, type={self.violation_type}, severity={self.severity})>"
