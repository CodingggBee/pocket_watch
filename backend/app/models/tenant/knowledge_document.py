"""Knowledge document — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
import enum


class DocumentType(str, enum.Enum):
    MANUAL = "manual"
    TROUBLESHOOTING = "troubleshooting"
    SOP = "sop"
    TRAINING = "training"


class KnowledgeDocument(TenantBase):
    """Uploaded document for RAG AI coaching — tenant schema"""

    __tablename__ = "knowledge_documents"

    document_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plant_id = Column(String(36), ForeignKey("plants.plant_id"), nullable=True, index=True)
    document_title = Column(String(500), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    uploaded_by = Column(String(36), nullable=False)  # user_id of uploader
    is_processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<KnowledgeDocument(id={self.document_id}, title={self.document_title})>"
