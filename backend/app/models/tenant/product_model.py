"""Product model — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class ProductModel(TenantBase):
    """Product model produced on a production line"""

    __tablename__ = "product_models"

    model_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    line_id = Column(
        String(36), ForeignKey("production_lines.line_id"), nullable=False, index=True
    )
    model_name = Column(String(255), nullable=False)
    model_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    product_specs = Column(JSONB, nullable=True)  # was 'specifications' / 'metadata'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProductModel(id={self.model_id}, name={self.model_name})>"
