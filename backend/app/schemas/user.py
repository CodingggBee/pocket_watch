"""Pydantic schema for user (admin) profile response"""

from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    company_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone_country_code: Optional[str] = None
    is_verified: bool
    is_active: bool
    profile_completed: bool = False
    created_at: str

    class Config:
        from_attributes = True
