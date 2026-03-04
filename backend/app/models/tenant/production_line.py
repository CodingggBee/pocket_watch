"""Production line model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text


class ProductionLine(TenantBase):
    """Production line within a department"""

    __tablename__ = "production_lines"

    line_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=False, index=True)
    department_id = Column(
        String(36), ForeignKey("departments.department_id"), nullable=False, index=True
    )
    line_name = Column(String(255), nullable=False)
    line_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProductionLine(id={self.line_id}, name={self.line_name})>"
