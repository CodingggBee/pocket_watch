"""Pydantic schema for user (admin) profile response"""

from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    company_id: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True
