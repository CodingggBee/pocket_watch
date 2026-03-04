"""Station metrics — tenant schema"""
import uuid
from datetime import date, datetime
from app.database import TenantBase
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String


class StationMetric(TenantBase):
    """Daily aggregated metrics for a station"""

    __tablename__ = "station_metrics"

    metric_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    station_id = Column(
        String(36), ForeignKey("stations.station_id"), nullable=False, index=True
    )
    metric_date = Column(Date, nullable=False, default=date.today)
    not_in_control_count = Column(Integer, default=0, nullable=False)
    not_capable_count = Column(Integer, default=0, nullable=False)
    out_of_spec_count = Column(Integer, default=0, nullable=False)
    missing_checks_count = Column(Integer, default=0, nullable=False)
    total_samples = Column(Integer, default=0, nullable=False)
    oee_percentage = Column(Numeric(5, 2), nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<StationMetric(station={self.station_id}, date={self.metric_date})>"
