"""Sampling instruction — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text


class SamplingInstruction(TenantBase):
    """Step-by-step sampling instructions for a characteristic"""

    __tablename__ = "sampling_instructions"

    instruction_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    characteristic_id = Column(
        String(36), ForeignKey("characteristics.characteristic_id"), nullable=False, index=True
    )
    instruction_text = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SamplingInstruction(id={self.instruction_id}, order={self.order_index})>"
