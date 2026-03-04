"""Setup progress tracking — tenant schema"""
import uuid
from datetime import datetime
from app.database import TenantBase
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
import enum


class SetupStep(str, enum.Enum):
    """Setup wizard steps"""
    PLANT_SETUP = "plant_setup"
    DEPARTMENTS = "departments"
    LINES_MODELS = "lines_models"
    STATIONS = "stations"
    USERS = "users"
    COMPLETED = "completed"


class SetupProgress(TenantBase):
    """Tracks user's progress through the setup wizard"""

    __tablename__ = "setup_progress"

    progress_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plant_id = Column(
        String(36), ForeignKey("plants.plant_id", ondelete="CASCADE"), 
        nullable=False, unique=True, index=True
    )
    
    # Current step
    current_step = Column(
        SQLEnum(SetupStep), 
        nullable=False, 
        default=SetupStep.PLANT_SETUP
    )
    
    # Completion flags for each step
    plant_setup_completed = Column(Boolean, default=False, nullable=False)
    departments_completed = Column(Boolean, default=False, nullable=False)
    lines_models_completed = Column(Boolean, default=False, nullable=False)
    stations_completed = Column(Boolean, default=False, nullable=False)
    users_completed = Column(Boolean, default=False, nullable=False)
    
    # Overall completion
    setup_completed = Column(Boolean, default=False, nullable=False)
    
    # Additional wizard state (optional JSON field)
    wizard_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    last_updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<SetupProgress(plant={self.plant_id}, step={self.current_step}, completed={self.setup_completed})>"
