"""Setup Wizard API Routes — Complete 5-screen flow"""

from app.routes.auth import get_current_admin
from app.database import get_tenant_db, get_db
from app.models.admin import Admin
from app.models.company import Company
from app.models.plan import CompanySubscription, PlanType
from app.models.tenant.plant import Plant
from app.models.tenant.shift import Shift
from app.models.tenant.setup_progress import SetupProgress, SetupStep
from app.models.tenant.department import Department
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.product_model import ProductModel
from app.models.tenant.station import Station
from app.models.tenant.characteristic import Characteristic, ChartType
from app.models.tenant.user import User
from app.models.tenant.plant_membership import PlantMembership, PlantRole
from app.models.tenant.offsite_access_grant import OffsiteAccessGrant
from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import random

router = APIRouter(prefix="/admin/setup", tags=["Setup Wizard"])

# Password/PIN hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== Helper Functions ====================

def _generate_pin() -> str:
    """Generate a 4-digit PIN"""
    return str(random.randint(1000, 9999))


def _hash_pin(pin: str) -> str:
    """Hash PIN using bcrypt"""
    return pwd_context.hash(pin)


async def _send_user_welcome_notification(
    phone_country_code: str,
    phone_number: str,
    email: Optional[str],
    first_name: str,
    pin: str,
):
    """Send welcome notification with PIN and app download link"""
    message = f"""Welcome to PocketWatch, {first_name}!

Your login PIN: {pin}

Download the PocketWatch app:
📱 iOS: https://apps.apple.com/pocketwatch
📱 Android: https://play.google.com/store/apps/pocketwatch

You'll need to verify your phone number with an OTP when you first sign in.

Questions? Contact your manager or visit support.pocketwatch.com"""
    
    full_phone = f"{phone_country_code}{phone_number}"
    
    # Try to send SMS (if SMS service configured)
    try:
        from app.services.sms import send_sms
        await send_sms(full_phone, message)
        print(f"[USER SETUP] SMS sent to {full_phone}")
    except Exception as e:
        print(f"[USER SETUP] SMS send failed: {e}")
    
    # Send email if provided
    if email:
        try:
            from app.services.email import send_email
            await send_email(
                to_email=email,
                subject="Welcome to PocketWatch - Your Login PIN",
                body=message
            )
            print(f"[USER SETUP] Email sent to {email}")
        except Exception as e:
            print(f"[USER SETUP] Email send failed: {e}")

def _get_tenant_db(admin: Admin) -> Session:
    """Get tenant database session"""
    gen = get_tenant_db(admin.company_id)
    return next(gen)


def _parse_time(time_str: str) -> time:
    """Convert '08:00 AM' to time object"""
    dt = datetime.strptime(time_str, '%I:%M %p')
    return dt.time()


def _format_time(time_obj: time) -> str:
    """Convert time object to '08:00 AM'"""
    dt = datetime.combine(datetime.today(), time_obj)
    return dt.strftime('%I:%M %p')


def _check_setup_access(admin: Admin, db: Session) -> CompanySubscription:
    """Check subscription and return it"""
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.company_id == admin.company_id
    ).first()
    
    if not subscription:
        # Auto-create FREE plan
        subscription = CompanySubscription(
            company_id=admin.company_id,
            plan_type=PlanType.FREE,
            stations_count=1,
            monthly_cost=0,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription


def _ensure_tenant_schema(admin: Admin, tenant_db: Session) -> Session:
    """Ensure tenant schema exists, provision if needed"""
    try:
        # Test if plants table exists with raw SQL query - must fetch to execute
        result = tenant_db.execute(text("SELECT 1 FROM plants LIMIT 1"))
        result.fetchone()  # Force query execution
        return tenant_db
    except Exception as e:
        error_str = str(e).lower()
        # Check for various "table doesn't exist" error patterns
        if "does not exist" in error_str or "relation" in error_str or "undefined" in error_str:
            print(f"[PROVISION] Tenant schema missing tables for company {admin.company_id}, provisioning now...")
            
            # Close bad session
            try:
                tenant_db.rollback()
                tenant_db.close()
            except:
                pass
            
            # Provision tenant tables
            from app.utils.schema import provision_tenant_tables
            provision_tenant_tables(admin.company_id)
            print(f"[PROVISION] Tables created successfully for company {admin.company_id}")
            
            # Return fresh session with correct search_path
            gen = get_tenant_db(admin.company_id)
            new_session = next(gen)
            
            # Verify the tables were actually created
            try:
                result = new_session.execute(text("SELECT 1 FROM plants LIMIT 1"))
                result.fetchone()
                print(f"[PROVISION] Verified: plants table exists and is accessible")
                return new_session
            except Exception as verify_error:
                print(f"[PROVISION ERROR] Tables still not accessible after provision: {verify_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to provision tenant database schema. Please contact support."
                )
        raise


#==================== Schemas ====================

class ShiftCreate(BaseModel):
    start_time: str = Field(..., description="HH:MM AM/PM format")
    end_time: str = Field(..., description="HH:MM AM/PM format")
    shift_name: Optional[str] = None

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%I:%M %p')
            return v
        except ValueError:
            raise ValueError("Time must be in HH:MM AM/PM format")


class PlantSetupRequest(BaseModel):
    company_name: str
    plant_name: str
    address: str
    shifts: List[ShiftCreate] = Field(..., min_length=1)


class DepartmentCreate(BaseModel):
    department_name: str
    department_code: Optional[str] = None


class ProductModelCreate(BaseModel):
    model_name: str
    model_code: str


class LineCreate(BaseModel):
    line_name: str
    models: List[ProductModelCreate] = Field(..., min_length=1)


class LinesModelsRequest(BaseModel):
    department_id: str
    lines: List[LineCreate] = Field(..., min_length=1)


class CharacteristicCreate(BaseModel):
    characteristic_name: str
    unit_of_measure: Optional[str] = None
    target_value: Optional[float] = None
    usl: Optional[float] = Field(None, description="Upper Spec Limit")
    lsl: Optional[float] = Field(None, description="Lower Spec Limit")
    ucl: Optional[float] = Field(None, description="Upper Control Limit")
    lcl: Optional[float] = Field(None, description="Lower Control Limit")
    sample_size: Optional[int] = None
    check_frequency_minutes: Optional[int] = None
    chart_type: Optional[str] = "I-MR"


class StationSetupRequest(BaseModel):
    station_name: str
    department_id: str
    line_id: str
    model_id: str
    characteristics: List[CharacteristicCreate] = Field(..., min_length=1)
    sampling_frequency_minutes: Optional[int] = None


class UserSetupCreate(BaseModel):
    role: str = Field(..., description="'manager' or 'member'")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_country_code: str = Field(..., description="e.g., '+1', '+91'")
    phone_number: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    shift_id: str = Field(..., description="Shift UUID from shifts dropdown")
    offsite_permission: bool = Field(default=False, description="Allow offsite access")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v.lower() not in ['manager', 'member']:
            raise ValueError("Role must be 'manager' or 'member'")
        return v.lower()
    
    @field_validator('phone_country_code')
    @classmethod
    def validate_country_code(cls, v):
        if not v.startswith('+'):
            v = '+' + v
        return v


class UsersSetupRequest(BaseModel):
    plant_id: str
    users: List[UserSetupCreate] = Field(..., min_length=1, description="At least one user required")


# ==================== Endpoints ====================

@router.get("/status")
async def get_setup_status(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get current setup progress"""
    subscription = _check_setup_access(current_admin, db)
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Get or create plant
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        
        if not plant:
            return {
                "setup_required": True,
                "current_step": "plant_setup",
                "completed": False,
                "plant_id": None,
                "plan_type": subscription.plan_type.value,
                "stations_limit": 1 if subscription.plan_type == PlanType.FREE else subscription.stations_count
            }
        
        # Get setup progress
        progress = tenant_db.query(SetupProgress).filter(
            SetupProgress.plant_id == plant.plant_id
        ).first()
        
        if not progress:
            # Create progress tracker
            progress = SetupProgress(
                plant_id=plant.plant_id,
                current_step=SetupStep.PLANT_SETUP,
                plant_setup_completed=True  # Plant exists
            )
            tenant_db.add(progress)
            tenant_db.commit()
            tenant_db.refresh(progress)
        
        return {
            "setup_required": not progress.setup_completed,
            "current_step": progress.current_step.value,
            "completed": progress.setup_completed,
            "plant_id": plant.plant_id,
            "plant_setup_completed": progress.plant_setup_completed,
            "departments_completed": progress.departments_completed,
            "lines_models_completed": progress.lines_models_completed,
            "stations_completed": progress.stations_completed,
            "users_completed": progress.users_completed,
            "plan_type": subscription.plan_type.value,
            "stations_limit": 1 if subscription.plan_type == PlanType.FREE else subscription.stations_count
        }
    finally:
        tenant_db.close()


@router.get("/debug/schema-check")
async def debug_schema_check(
    current_admin: Admin = Depends(get_current_admin),
):
    """Debug endpoint: Check if tenant schema and tables exist"""
    from app.utils.schema import get_schema_name
    
    tenant_db = _get_tenant_db(current_admin)
    schema = get_schema_name(current_admin.company_id)
    
    try:
        # Check if schema exists
        result = tenant_db.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = :schema
        """), {"schema": schema})
        schema_exists = result.fetchone() is not None
        
        # Check which tables exist
        result = tenant_db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = :schema
            ORDER BY table_name
        """), {"schema": schema})
        tables = [row[0] for row in result.fetchall()]
        
        # Check search_path
        result = tenant_db.execute(text("SHOW search_path"))
        search_path = result.fetchone()[0]
        
        return {
            "company_id": current_admin.company_id,
            "schema_name": schema,
            "schema_exists": schema_exists,
            "current_search_path": search_path,
            "tables_found": len(tables),
            "tables": tables,
            "has_plants_table": "plants" in tables,
            "has_shifts_table": "shifts" in tables,
            "has_setup_progress_table": "setup_progress" in tables,
        }
    except Exception as e:
        return {
            "error": str(e),
            "company_id": current_admin.company_id,
            "schema_name": schema
        }
    finally:
        tenant_db.close()


@router.post("/screen1-plant", status_code=status.HTTP_201_CREATED)
async def setup_plant(
    data: PlantSetupRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Screen 1: Plant Setup"""
    subscription = _check_setup_access(current_admin, db)
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Update company name
        company = db.query(Company).filter(Company.company_id == current_admin.company_id).first()
        if company:
            company.company_name = data.company_name
            db.commit()
        
        # Create plant
        plant = Plant(
            plant_name=data.plant_name,
            address=data.address,
            is_active=True
        )
        tenant_db.add(plant)
        tenant_db.flush()
        
        # Create shifts
        for shift_data in data.shifts:
            shift = Shift(
                plant_id=plant.plant_id,
                start_time=_parse_time(shift_data.start_time),
                end_time=_parse_time(shift_data.end_time),
                shift_name=shift_data.shift_name
            )
            tenant_db.add(shift)
        
        # Create setup progress tracker
        progress = SetupProgress(
            plant_id=plant.plant_id,
            current_step=SetupStep.DEPARTMENTS,
            plant_setup_completed=True
        )
        tenant_db.add(progress)
        
        tenant_db.commit()
        
        return {
            "message": "Plant setup completed",
            "plant_id": plant.plant_id,
            "next_step": "departments"
        }
    finally:
        tenant_db.close()


@router.post("/screen2-departments", status_code=status.HTTP_201_CREATED)
async def setup_departments(
    departments: List[DepartmentCreate],
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 2: Add Departments"""
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")
        
        # Create departments
        created_depts = []
        for dept_data in departments:
            dept = Department(
                plant_id=plant_id,
                department_name=dept_data.department_name,
                department_code=dept_data.department_code,
                is_active=True
            )
            tenant_db.add(dept)
            created_depts.append(dept)
        
        # Update progress
        progress = tenant_db.query(SetupProgress).filter(
            SetupProgress.plant_id == plant_id
        ).first()
        
        if progress:
            progress.departments_completed = True
            progress.current_step = SetupStep.LINES_MODELS
            progress.last_updated_at = datetime.utcnow()
        
        tenant_db.commit()
        
        return {
            "message": f"Created {len(created_depts)} departments",
            "department_ids": [d.department_id for d in created_depts],
            "next_step": "lines_models"
        }
    finally:
        tenant_db.close()


@router.post("/screen3-lines-models", status_code=status.HTTP_201_CREATED)
async def setup_lines_and_models(
    data: LinesModelsRequest,
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 3: Add Production Lines and Models"""
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Verify department exists
        dept = tenant_db.query(Department).filter(
            Department.department_id == data.department_id
        ).first()
        if not dept:
            raise HTTPException(404, detail="Department not found")
        
        created_lines = []
        created_models = []
        
        for line_data in data.lines:
            # Create production line
            line = ProductionLine(
                plant_id=plant_id,
                department_id=data.department_id,
                line_name=line_data.line_name,
                is_active=True
            )
            tenant_db.add(line)
            tenant_db.flush()
            created_lines.append(line)
            
            # Create models for this line
            for model_data in line_data.models:
                model = ProductModel(
                    line_id=line.line_id,
                    model_name=model_data.model_name,
                    model_code=model_data.model_code,
                    is_active=True
                )
                tenant_db.add(model)
                created_models.append(model)
        
        # Update progress
        progress = tenant_db.query(SetupProgress).filter(
            SetupProgress.plant_id == plant_id
        ).first()
        
        if progress:
            progress.lines_models_completed = True
            progress.current_step = SetupStep.STATIONS
            progress.last_updated_at = datetime.utcnow()
        
        tenant_db.commit()
        
        return {
            "message": f"Created {len(created_lines)} lines with {len(created_models)} models",
            "line_ids": [l.line_id for l in created_lines],
            "model_ids": [m.model_id for m in created_models],
            "next_step": "stations"
        }
    finally:
        tenant_db.close()


@router.post("/screen4-station", status_code=status.HTTP_201_CREATED)
async def setup_station(
    data: StationSetupRequest,
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Screen 4: Setup Station with Quality Control Settings"""
    subscription = _check_setup_access(current_admin, db)
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Check station quota
        station_count = tenant_db.query(Station).filter(
            Station.plant_id == plant_id,
            Station.operational_status == "active"
        ).count()
        
        if subscription.plan_type == PlanType.FREE and station_count >= 1:
            raise HTTPException(
                403,
                detail="Free plan limited to 1 station. Upgrade to Premium for unlimited stations."
            )
        
        if subscription.plan_type == PlanType.PREMIUM and station_count >= subscription.stations_count:
            raise HTTPException(
                403,
                detail=f"Station limit reached ({subscription.stations_count}). Increase your station count in Plans."
            )
        
        # Create station
        station = Station(
            plant_id=plant_id,
            department_id=data.department_id,
            line_id=data.line_id,
            station_name=data.station_name,
            sampling_frequency_minutes=data.sampling_frequency_minutes,
            operational_status="active"
        )
        tenant_db.add(station)
        tenant_db.flush()
        
        # Create characteristics
        for char_data in data.characteristics:
            characteristic = Characteristic(
                station_id=station.station_id,
                characteristic_name=char_data.characteristic_name,
                unit_of_measure=char_data.unit_of_measure,
                target_value=char_data.target_value,
                usl=char_data.usl,
                lsl=char_data.lsl,
                ucl=char_data.ucl,
                lcl=char_data.lcl,
                sample_size=char_data.sample_size,
                check_frequency_minutes=char_data.check_frequency_minutes,
                chart_type=ChartType(char_data.chart_type) if char_data.chart_type else ChartType.I_MR,
                is_active=True
            )
            tenant_db.add(characteristic)
        
        tenant_db.commit()
        
        return {
            "message": "Station created successfully",
            "station_id": station.station_id,
            "characteristics_count": len(data.characteristics)
        }
    finally:
        tenant_db.close()


@router.get("/shifts")
async def get_shifts_for_setup(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get list of shifts for user setup dropdown"""
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")
        
        # Get all shifts for this plant
        shifts = tenant_db.query(Shift).filter(
            Shift.plant_id == plant_id
        ).order_by(Shift.start_time).all()
        
        if not shifts:
            raise HTTPException(400, detail="No shifts found. Please complete Plant Setup first.")
        
        return {
            "plant_id": plant_id,
            "shifts": [
                {
                    "shift_id": shift.shift_id,
                    "shift_name": shift.shift_name or f"Shift {_format_time(shift.start_time)} - {_format_time(shift.end_time)}",
                    "start_time": _format_time(shift.start_time),
                    "end_time": _format_time(shift.end_time),
                }
                for shift in shifts
            ]
        }
    finally:
        tenant_db.close()


@router.post("/screen5-users", status_code=status.HTTP_201_CREATED)
async def setup_users(
    data: UsersSetupRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 5: User Setup — Add team members and complete setup"""
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == data.plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")
        
        # Get setup progress
        progress = tenant_db.query(SetupProgress).filter(
            SetupProgress.plant_id == data.plant_id
        ).first()
        
        if not progress:
            raise HTTPException(404, detail="Setup progress not found")
        
        # Verify at least one user
        if len(data.users) == 0:
            raise HTTPException(400, detail="At least one user required")
        
        created_users = []
        
        for user_data in data.users:
            # Check if user already exists
            full_phone = f"{user_data.phone_country_code}{user_data.phone_number}"
            existing_user = tenant_db.query(User).filter(
                User.phone_number == full_phone
            ).first()
            
            if existing_user:
                raise HTTPException(
                    400,
                    detail=f"User with phone {full_phone} already exists"
                )
            
            # Verify shift exists
            shift = tenant_db.query(Shift).filter(
                Shift.shift_id == user_data.shift_id,
                Shift.plant_id == data.plant_id
            ).first()
            
            if not shift:
                raise HTTPException(
                    400,
                    detail=f"Shift {user_data.shift_id} not found for this plant"
                )
            
            # Generate PIN and hash it
            pin = _generate_pin()
            pin_hash = _hash_pin(pin)
            
            # Create user
            full_name = f"{user_data.first_name} {user_data.last_name}"
            new_user = User(
                phone_number=full_phone,
                phone_country_code=user_data.phone_country_code,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                full_name=full_name,
                email=user_data.email,
                default_shift_id=user_data.shift_id,
                pin_hash=pin_hash,
                phone_verified=False,
                is_active=True
            )
            tenant_db.add(new_user)
            tenant_db.flush()
            
            # Create plant membership with role
            role = PlantRole.MANAGER if user_data.role == 'manager' else PlantRole.MEMBER
            membership = PlantMembership(
                plant_id=data.plant_id,
                user_id=new_user.user_id,
                role=role,
                invited_by=current_admin.id,
                accepted_at=None,  # Will accept when they first login
                is_active=True
            )
            tenant_db.add(membership)
            
            # Create offsite access grant if needed
            if user_data.offsite_permission:
                offsite_grant = OffsiteAccessGrant(
                    plant_id=data.plant_id,
                    user_id=new_user.user_id,
                    granted_by=current_admin.id,
                    is_active=True
                )
                tenant_db.add(offsite_grant)
            
            # Send welcome notification with PIN
            try:
                await _send_user_welcome_notification(
                    user_data.phone_country_code,
                    user_data.phone_number,
                    user_data.email,
                    user_data.first_name,
                    pin
                )
            except Exception as e:
                print(f"[USER SETUP] Failed to send notification: {e}")
                # Continue even if notification fails
            
            created_users.append({
                "user_id": new_user.user_id,
                "full_name": full_name,
                "phone": full_phone,
                "email": user_data.email,
                "role": user_data.role,
                "shift_id": user_data.shift_id,
                "offsite_permission": user_data.offsite_permission,
                "pin_sent": True  # Notification attempted
            })
        
        # Mark user setup as completed
        progress.users_completed = True
        progress.setup_completed = True
        progress.current_step = SetupStep.COMPLETED
        progress.completed_at = datetime.utcnow()
        
        tenant_db.commit()
        
        return {
            "message": "Users created successfully! Setup completed.",
            "users_created": len(created_users),
            "users": created_users,
            "setup_completed": True,
            "redirect_to": "dashboard"
        }
    finally:
        tenant_db.close()


@router.post("/complete")
async def complete_setup(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Mark setup as completed"""
    tenant_db = _get_tenant_db(current_admin)
    
    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)
        
        progress = tenant_db.query(SetupProgress).filter(
            SetupProgress.plant_id == plant_id
        ).first()
        
        if not progress:
            raise HTTPException(404, detail="Setup progress not found")
        
        # Verify at least one station exists
        station_count = tenant_db.query(Station).filter(
            Station.plant_id == plant_id
        ).count()
        
        if station_count == 0:
            raise HTTPException(400, detail="At least one station required to complete setup")
        
        progress.stations_completed = True
        progress.setup_completed = True
        progress.current_step = SetupStep.COMPLETED
        progress.completed_at = datetime.utcnow()
        tenant_db.commit()
        
        return {
            "message": "Setup completed successfully!",
            "setup_completed": True,
            "redirect_to": "dashboard"
        }
    finally:
        tenant_db.close()


@router.post("/add-station", status_code=status.HTTP_201_CREATED)
async def add_new_station(
    data: StationSetupRequest,
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Add a new station from anywhere in the app (post-setup)"""
    # Same logic as screen4-station
    return await setup_station(data, plant_id, current_admin, db)
