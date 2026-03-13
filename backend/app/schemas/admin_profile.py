"""Comprehensive admin profile response schema for /me endpoint"""

from typing import List, Optional

from pydantic import BaseModel

# ==================== Nested Response Models ====================


class ShiftResponse(BaseModel):
    shift_id: str
    shift_name: Optional[str]
    start_time: str  # "08:00 AM"
    end_time: str  # "04:00 PM"


class PlantResponse(BaseModel):
    plant_id: str
    plant_name: str
    plant_code: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    timezone: Optional[str]
    is_active: bool
    geofence_radius_meters: int
    shifts: List[ShiftResponse] = []


class DepartmentResponse(BaseModel):
    department_id: str
    department_name: str
    plant_id: str


class ProductModelResponse(BaseModel):
    model_id: str
    model_name: str
    model_code: str


class ProductionLineResponse(BaseModel):
    line_id: str
    line_name: str
    department_id: str
    models: List[ProductModelResponse] = []


class CharacteristicResponse(BaseModel):
    characteristic_id: str
    characteristic_name: str
    unit_of_measure: Optional[str]
    lsl: Optional[float]
    usl: Optional[float]
    target_value: Optional[float]
    check_frequency_minutes: Optional[int]
    sample_size: int
    chart_type: str


class StationResponse(BaseModel):
    station_id: str
    station_name: str
    station_code: Optional[str]
    department_id: str
    line_id: str
    operational_status: str  # "active" or "inactive"
    sampling_frequency_minutes: Optional[int]
    characteristics: List[CharacteristicResponse] = []


class UserResponse(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    full_name: str
    phone_country_code: str
    phone_number: str
    email: Optional[str]
    role: str
    is_active: bool
    phone_verified: bool


class SetupProgressResponse(BaseModel):
    current_step: str
    plant_setup_completed: bool
    departments_completed: bool
    lines_models_completed: bool
    stations_completed: bool
    users_completed: bool
    setup_completed: bool
    started_at: str
    completed_at: Optional[str]
    last_updated_at: str


class SubscriptionResponse(BaseModel):
    plan_type: str
    stations_count: int
    monthly_cost: float
    is_active: bool


class CompanyResponse(BaseModel):
    company_id: str
    company_name: Optional[str]
    is_active: bool
    created_at: str


class UserBasicInfo(BaseModel):
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone_country_code: Optional[str] = None
    is_verified: bool = True
    is_active: bool = True
    profile_completed: bool = True
    role: str = "admin"
    created_at: Optional[str] = None


# ==================== Main Response Model ====================


class DetailedProfileResponse(BaseModel):
    """Comprehensive profile with all setup data for admins or invitees"""

    # User info
    user: UserBasicInfo

    # Company info
    company: CompanyResponse

    # Subscription/plan
    subscription: SubscriptionResponse

    # Setup progress
    setup_progress: Optional[SetupProgressResponse]

    # Summary / Convenience fields
    is_admin: bool = True
    subscription_type: str = "free"
    active_plant_id: Optional[str] = None
    setup_completed: bool = False

    # All setup data
    plants: List[PlantResponse] = []
    departments: List[DepartmentResponse] = []
    production_lines: List[ProductionLineResponse] = []
    stations: List[StationResponse] = []
    users: List[UserResponse] = []

    # Summary counts
    summary: dict = {
        "total_plants": 0,
        "total_departments": 0,
        "total_lines": 0,
        "total_stations": 0,
        "total_users": 0,
        "total_characteristics": 0,
    }

    class Config:
        from_attributes = True
