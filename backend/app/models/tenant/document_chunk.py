"""Document chunk — tenant schema (text chunk metadata; vectors stored in Pinecone)"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class DocumentChunk(TenantBase):
    """
    Text chunk from a knowledge document.
    The actual embedding vector is stored in Pinecone — `pinecone_id` references it.
    """

    __tablename__ = "document_chunks"

    chunk_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("knowledge_documents.document_id"), nullable=False, index=True
    )
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    pinecone_id = Column(String(255), nullable=True, index=True)  # ID in Pinecone index
    chunk_metadata = Column(JSONB, nullable=True)  # Extra metadata for Pinecone (column named chunk_metadata — 'metadata' is reserved by SQLAlchemy)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DocumentChunk(id={self.chunk_id}, index={self.chunk_index})>"
