"""Department model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text


class Department(TenantBase):
    """Department within a plant"""

    __tablename__ = "departments"

    department_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    department_name = Column(String(255), nullable=False)
    department_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Department(id={self.department_id}, name={self.department_name})>"
