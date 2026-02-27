"""Company usage — tenant schema"""
import uuid
from datetime import date, datetime
from app.database import TenantBase
from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String


class CompanyUsage(TenantBase):
    """Daily usage stats aggregated across the tenant"""

    __tablename__ = "company_usage"

    usage_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=True, index=True)
    usage_date = Column(Date, nullable=False, default=date.today)
    total_billable_stations = Column(Integer, default=0, nullable=False)
    total_pending_stations = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)
    samples_collected = Column(Integer, default=0, nullable=False)
    ai_queries = Column(Integer, default=0, nullable=False)
    storage_used_mb = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CompanyUsage(plant={self.plant_id}, date={self.usage_date})>"
