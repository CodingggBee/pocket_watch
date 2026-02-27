"""SPC calculation model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB


class SPCCalculation(TenantBase):
    """SPC calculated statistics for a sample"""

    __tablename__ = "spc_calculations"

    calculation_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sample_id = Column(
        String(36), ForeignKey("samples.sample_id"), nullable=False, index=True
    )
    characteristic_id = Column(
        String(36), ForeignKey("characteristics.characteristic_id"), nullable=False, index=True
    )
    xbar = Column(Numeric(15, 6), nullable=True)
    r_value = Column(Numeric(15, 6), nullable=True)
    moving_range = Column(Numeric(15, 6), nullable=True)
    sigma = Column(Numeric(15, 6), nullable=True)
    cpk = Column(Numeric(10, 4), nullable=True)
    cp = Column(Numeric(10, 4), nullable=True)
    rules_violated = Column(JSONB, nullable=True)  # e.g. ["Rule 1", "Rule 2"]
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SPCCalculation(id={self.calculation_id}, cpk={self.cpk})>"
