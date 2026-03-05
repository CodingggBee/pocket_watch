"""Setup Wizard API Routes — Complete 5-screen flow"""

import random
from datetime import datetime, time
from typing import List, Optional

from app.database import get_db, get_tenant_db
from app.models.admin import Admin
from app.models.company import Company
from app.models.plan import CompanySubscription, PlanType
from app.models.tenant.characteristic import Characteristic, ChartType
from app.models.tenant.department import Department
from app.models.tenant.offsite_access_grant import OffsiteAccessGrant
from app.models.tenant.plant import Plant
from app.models.tenant.plant_membership import PlantMembership, PlantRole
from app.models.tenant.product_model import ProductModel
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.setup_progress import SetupProgress, SetupStep
from app.models.tenant.shift import Shift
from app.models.tenant.station import Station
from app.models.tenant.user import User
from app.routes.auth import get_current_admin
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

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
                body=message,
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
    dt = datetime.strptime(time_str, "%I:%M %p")
    return dt.time()


def _format_time(time_obj: time) -> str:
    """Convert time object to '08:00 AM'"""
    dt = datetime.combine(datetime.today(), time_obj)
    return dt.strftime("%I:%M %p")


def _check_setup_access(admin: Admin, db: Session) -> CompanySubscription:
    """Check subscription and return it"""
    subscription = (
        db.query(CompanySubscription)
        .filter(CompanySubscription.company_id == admin.company_id)
        .first()
    )

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
        if (
            "does not exist" in error_str
            or "relation" in error_str
            or "undefined" in error_str
        ):
            print(
                f"[PROVISION] Tenant schema missing tables for company {admin.company_id}, provisioning now..."
            )

            # Close bad session
            try:
                tenant_db.rollback()
                tenant_db.close()
            except:
                pass

            # Provision tenant tables
            from app.utils.schema import provision_tenant_tables

            provision_tenant_tables(admin.company_id)
            print(
                f"[PROVISION] Tables created successfully for company {admin.company_id}"
            )

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
                print(
                    f"[PROVISION ERROR] Tables still not accessible after provision: {verify_error}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to provision tenant database schema. Please contact support.",
                )
        raise


# ==================== Schemas ====================


class ShiftCreate(BaseModel):
    start_time: str = Field(..., description="HH:MM AM/PM format")
    end_time: str = Field(..., description="HH:MM AM/PM format")
    shift_name: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%I:%M %p")
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
    lsl: Optional[float] = Field(
        None, description="Lower Spec Limit — required for Cpk"
    )
    usl: Optional[float] = Field(
        None, description="Upper Spec Limit — required for Cpk"
    )
    check_frequency_minutes: Optional[int] = None
    # Optional: set sample_size > 1 to switch to Xbar-R, or chart_type = 'P-Chart' for attribute data
    sample_size: Optional[int] = Field(
        None,
        description="Items per subgroup. 1 = I-MR (default), >1 = Xbar-R, use 'P-Chart' type for attribute",
    )
    chart_type: Optional[str] = Field(
        None, description="'I-MR' (default), 'Xbar-R', or 'P-Chart'"
    )
    # target_value is backend-calculated from (lsl+usl)/2 — no need to send it
    target_value: Optional[float] = Field(
        None, description="Override auto-calculated midpoint. Normally leave null."
    )


class StationSetupRequest(BaseModel):
    station_name: str
    department_id: str
    line_id: str
    model_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of model UUIDs or model_codes (e.g. '100156AB') from the line's models",
    )
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

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v.lower() not in ["manager", "member"]:
            raise ValueError("Role must be 'manager' or 'member'")
        return v.lower()

    @field_validator("phone_country_code")
    @classmethod
    def validate_country_code(cls, v):
        if not v.startswith("+"):
            v = "+" + v
        return v


class UsersSetupRequest(BaseModel):
    plant_id: str
    users: List[UserSetupCreate] = Field(
        ..., min_length=1, description="At least one user required"
    )


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
                "stations_limit": (
                    1
                    if subscription.plan_type == PlanType.FREE
                    else subscription.stations_count
                ),
            }

        # Get setup progress
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant.plant_id)
            .first()
        )

        if not progress:
            # Create progress tracker
            progress = SetupProgress(
                plant_id=plant.plant_id,
                current_step=SetupStep.PLANT_SETUP,
                plant_setup_completed=True,  # Plant exists
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
            "stations_limit": (
                1
                if subscription.plan_type == PlanType.FREE
                else subscription.stations_count
            ),
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
        result = tenant_db.execute(
            text(
                """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = :schema
        """
            ),
            {"schema": schema},
        )
        schema_exists = result.fetchone() is not None

        # Check which tables exist
        result = tenant_db.execute(
            text(
                """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = :schema
            ORDER BY table_name
        """
            ),
            {"schema": schema},
        )
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
            "schema_name": schema,
        }
    finally:
        tenant_db.close()


@router.post("/screen1-plant", status_code=status.HTTP_201_CREATED)
async def setup_plant(
    data: PlantSetupRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Screen 1: Plant Setup - Creates or updates plant with shifts"""
    subscription = _check_setup_access(current_admin, db)
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Update company name
        company = (
            db.query(Company)
            .filter(Company.company_id == current_admin.company_id)
            .first()
        )
        if company:
            company.company_name = data.company_name
            db.commit()

        # Check if plant already exists (for the setup wizard, there should only be one active plant)
        existing_plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()

        if existing_plant:
            # UPDATE existing plant
            existing_plant.plant_name = data.plant_name
            existing_plant.address = data.address
            plant = existing_plant

            # Delete old shifts and create new ones
            tenant_db.query(Shift).filter(Shift.plant_id == plant.plant_id).delete()
        else:
            # CREATE new plant
            plant = Plant(
                plant_name=data.plant_name, address=data.address, is_active=True
            )
            tenant_db.add(plant)
            tenant_db.flush()

        # Create shifts (fresh set based on current form data)
        for shift_data in data.shifts:
            shift = Shift(
                plant_id=plant.plant_id,
                start_time=_parse_time(shift_data.start_time),
                end_time=_parse_time(shift_data.end_time),
                shift_name=shift_data.shift_name,
            )
            tenant_db.add(shift)

        # Get or create setup progress tracker
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant.plant_id)
            .first()
        )

        if not progress:
            progress = SetupProgress(
                plant_id=plant.plant_id,
                current_step=SetupStep.DEPARTMENTS,
                plant_setup_completed=True,
            )
            tenant_db.add(progress)
        else:
            # Update existing progress
            progress.plant_setup_completed = True
            progress.current_step = SetupStep.DEPARTMENTS
            progress.last_updated_at = datetime.utcnow()

        tenant_db.commit()

        return {
            "message": "Plant setup completed",
            "plant_id": plant.plant_id,
            "next_step": "departments",
        }
    finally:
        tenant_db.close()


@router.post("/screen2-departments", status_code=status.HTTP_201_CREATED)
async def setup_departments(
    departments: List[DepartmentCreate],
    plant_id: str,
    replace_all: bool = False,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 2: Add Departments - Creates or updates departments for the plant

    Args:
        departments: List of departments to create/update
        plant_id: Plant UUID
        replace_all: If True, deletes existing departments and replaces with new list.
                     If False (default), creates new departments or updates existing ones by name.
    """
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")

        if replace_all:
            # Replace mode: Delete all existing departments
            # (cascade will delete related lines/models/stations)
            tenant_db.query(Department).filter(Department.plant_id == plant_id).delete()

        # Get existing departments for this plant
        existing_depts = (
            tenant_db.query(Department).filter(Department.plant_id == plant_id).all()
        )
        existing_dept_names = {
            dept.department_name.lower(): dept for dept in existing_depts
        }

        created_or_updated_depts = []

        for dept_data in departments:
            dept_name_lower = dept_data.department_name.lower()

            if dept_name_lower in existing_dept_names:
                # Update existing department
                existing_dept = existing_dept_names[dept_name_lower]
                existing_dept.department_name = (
                    dept_data.department_name
                )  # Update with correct case
                existing_dept.is_active = True
                created_or_updated_depts.append(existing_dept)
            else:
                # Create new department
                new_dept = Department(
                    plant_id=plant_id,
                    department_name=dept_data.department_name,
                    is_active=True,
                )
                tenant_db.add(new_dept)
                created_or_updated_depts.append(new_dept)

        tenant_db.flush()  # Flush to get IDs

        # Update progress
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant_id)
            .first()
        )

        if progress:
            progress.departments_completed = True
            progress.current_step = SetupStep.LINES_MODELS
            progress.last_updated_at = datetime.utcnow()

            # Save department IDs to wizard_metadata for tracking
            if not progress.wizard_metadata:
                progress.wizard_metadata = {}
            progress.wizard_metadata["department_ids"] = [
                d.department_id for d in created_or_updated_depts
            ]

        tenant_db.commit()

        return {
            "message": f"Processed {len(created_or_updated_depts)} departments",
            "department_ids": [d.department_id for d in created_or_updated_depts],
            "next_step": "lines_models",
        }
    finally:
        tenant_db.close()


@router.post("/screen3-lines-models", status_code=status.HTTP_201_CREATED)
async def setup_lines_and_models(
    data: LinesModelsRequest,
    plant_id: str,
    replace_all: bool = False,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 3: Add Production Lines and Models - Creates or updates lines/models for a department

    Args:
        data: Lines and models data
        plant_id: Plant UUID
        replace_all: If True, deletes existing lines/models for this department and replaces with new list.
                     If False (default), creates new lines or updates existing ones by name.
    """
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Verify department exists
        dept = (
            tenant_db.query(Department)
            .filter(Department.department_id == data.department_id)
            .first()
        )
        if not dept:
            raise HTTPException(404, detail="Department not found")

        if replace_all:
            # Replace mode: Delete existing lines for this department
            # (cascade will delete related models and stations)
            tenant_db.query(ProductionLine).filter(
                ProductionLine.department_id == data.department_id
            ).delete()

        # Get existing lines for this department
        existing_lines = (
            tenant_db.query(ProductionLine)
            .filter(ProductionLine.department_id == data.department_id)
            .all()
        )
        existing_line_names = {line.line_name.lower(): line for line in existing_lines}

        created_or_updated_lines = []
        created_or_updated_models = []

        for line_data in data.lines:
            line_name_lower = line_data.line_name.lower()

            if line_name_lower in existing_line_names:
                # Update existing line
                line = existing_line_names[line_name_lower]
                line.line_name = line_data.line_name  # Update with correct case
                line.is_active = True
            else:
                # Create new production line
                line = ProductionLine(
                    plant_id=plant_id,
                    department_id=data.department_id,
                    line_name=line_data.line_name,
                    is_active=True,
                )
                tenant_db.add(line)
                tenant_db.flush()

            created_or_updated_lines.append(line)

            # Get existing models for this line
            existing_models = (
                tenant_db.query(ProductModel)
                .filter(ProductModel.line_id == line.line_id)
                .all()
            )
            existing_model_codes = {
                model.model_code.lower(): model for model in existing_models
            }

            # Create or update models for this line
            for model_data in line_data.models:
                model_code_lower = model_data.model_code.lower()

                if model_code_lower in existing_model_codes:
                    # Update existing model
                    model = existing_model_codes[model_code_lower]
                    model.model_name = model_data.model_name
                    model.model_code = model_data.model_code
                    model.is_active = True
                else:
                    # Create new model
                    model = ProductModel(
                        line_id=line.line_id,
                        model_name=model_data.model_name,
                        model_code=model_data.model_code,
                        is_active=True,
                    )
                    tenant_db.add(model)

                created_or_updated_models.append(model)

        # Update progress
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant_id)
            .first()
        )

        if progress:
            progress.lines_models_completed = True
            progress.current_step = SetupStep.STATIONS
            progress.last_updated_at = datetime.utcnow()

            # Save line/model IDs to wizard_metadata for tracking
            if not progress.wizard_metadata:
                progress.wizard_metadata = {}
            progress.wizard_metadata["line_ids"] = [
                l.line_id for l in created_or_updated_lines
            ]
            progress.wizard_metadata["model_ids"] = [
                m.model_id for m in created_or_updated_models
            ]

        tenant_db.commit()

        return {
            "message": f"Processed {len(created_or_updated_lines)} lines with {len(created_or_updated_models)} models",
            "line_ids": [l.line_id for l in created_or_updated_lines],
            "model_ids": [m.model_id for m in created_or_updated_models],
            "next_step": "stations",
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
    """Screen 4: Setup Station with characteristics.

    - model_ids accepts model UUIDs or model_codes (e.g. '100156AB').
    - target_value is auto-calculated as (lsl + usl) / 2 if not supplied.
    - ucl / lcl are left null at setup and computed dynamically by the chart
      endpoints once sample data arrives (using a 30-sample rolling window).
    - chart_type defaults to 'I-MR'; pass 'P-Chart' for attribute/defective data.
    """
    subscription = _check_setup_access(current_admin, db)
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # ── Station quota guard ─────────────────────────────────────
        station_count = (
            tenant_db.query(Station)
            .filter(
                Station.plant_id == plant_id, Station.operational_status == "active"
            )
            .count()
        )

        if subscription.plan_type == PlanType.FREE and station_count >= 1:
            raise HTTPException(
                403,
                detail="Free plan limited to 1 station. Upgrade to Premium for unlimited stations.",
            )
        if (
            subscription.plan_type == PlanType.PREMIUM
            and station_count >= subscription.stations_count
        ):
            raise HTTPException(
                403,
                detail=f"Station limit reached ({subscription.stations_count}). Increase your station count in Plans.",
            )

        # ── Resolve model_ids (accept UUID or model_code) ───────────
        resolved_model_ids = []
        for model_ref in data.model_ids:
            model = (
                tenant_db.query(ProductModel)
                .filter(
                    or_(
                        ProductModel.model_id == model_ref,
                        ProductModel.model_code == model_ref,
                    ),
                    ProductModel.line_id == data.line_id,
                    ProductModel.is_active == True,
                )
                .first()
            )
            if model:
                resolved_model_ids.append(model.model_id)
            else:
                # Keep the raw ref if not found (so it's not silently dropped)
                resolved_model_ids.append(model_ref)

        # ── Validate department and line exist ────────────────────────
        dept = (
            tenant_db.query(Department)
            .filter(Department.department_id == data.department_id)
            .first()
        )
        if not dept:
            raise HTTPException(
                404,
                detail=f"Department '{data.department_id}' not found. Use GET /admin/setup/departments?plant_id=... to get valid IDs.",
            )

        line = (
            tenant_db.query(ProductionLine)
            .filter(ProductionLine.line_id == data.line_id)
            .first()
        )
        if not line:
            raise HTTPException(
                404,
                detail=f"Production line '{data.line_id}' not found. Use GET /admin/setup/lines?plant_id=...&department_id=... to get valid IDs.",
            )

        # ── Create station ──────────────────────────────────────────
        station = Station(
            plant_id=plant_id,
            department_id=data.department_id,
            line_id=data.line_id,
            station_name=data.station_name,
            sampling_frequency_minutes=data.sampling_frequency_minutes,
            model_ids=resolved_model_ids,
            operational_status="active",
            data_entry_locked=False,
        )
        tenant_db.add(station)
        tenant_db.flush()

        # ── Create characteristics ──────────────────────────────────
        for char_data in data.characteristics:
            # Auto-calculate target_value from spec midpoint
            target_value = char_data.target_value
            if (
                target_value is None
                and char_data.usl is not None
                and char_data.lsl is not None
            ):
                target_value = round(
                    (float(char_data.usl) + float(char_data.lsl)) / 2, 8
                )

            # Determine chart type
            if char_data.chart_type:
                try:
                    chart_type = ChartType(char_data.chart_type)
                except ValueError:
                    chart_type = ChartType.I_MR
            elif char_data.sample_size and char_data.sample_size > 1:
                chart_type = ChartType.XBAR_R
            else:
                chart_type = ChartType.I_MR

            characteristic = Characteristic(
                station_id=station.station_id,
                characteristic_name=char_data.characteristic_name,
                unit_of_measure=char_data.unit_of_measure,
                target_value=target_value,
                usl=char_data.usl,
                lsl=char_data.lsl,
                # ucl / lcl / cl are left null — computed dynamically from sample data
                ucl=None,
                lcl=None,
                cl=target_value,  # use spec midpoint as initial center-line display only
                sample_size=char_data.sample_size or 1,
                check_frequency_minutes=char_data.check_frequency_minutes,
                chart_type=chart_type,
                is_active=True,
            )
            tenant_db.add(characteristic)

        # ── Update setup progress ───────────────────────────────────
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant_id)
            .first()
        )
        if progress:
            progress.stations_completed = True
            progress.current_step = SetupStep.USERS
            progress.last_updated_at = datetime.utcnow()

        tenant_db.commit()

        return {
            "message": "Station created successfully",
            "station_id": station.station_id,
            "model_ids": resolved_model_ids,
            "characteristics_count": len(data.characteristics),
            "next_step": "users",
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
        shifts = (
            tenant_db.query(Shift)
            .filter(Shift.plant_id == plant_id)
            .order_by(Shift.start_time)
            .all()
        )

        if not shifts:
            raise HTTPException(
                400, detail="No shifts found. Please complete Plant Setup first."
            )

        return {
            "plant_id": plant_id,
            "shifts": [
                {
                    "shift_id": shift.shift_id,
                    "shift_name": shift.shift_name
                    or f"Shift {_format_time(shift.start_time)} - {_format_time(shift.end_time)}",
                    "start_time": _format_time(shift.start_time),
                    "end_time": _format_time(shift.end_time),
                }
                for shift in shifts
            ],
        }
    finally:
        tenant_db.close()


@router.get("/departments")
async def get_departments_list(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get list of departments for dropdowns in Screen 3 and 4"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")

        # Get all departments for this plant
        departments = (
            tenant_db.query(Department)
            .filter(Department.plant_id == plant_id, Department.is_active == True)
            .all()
        )

        if not departments:
            raise HTTPException(
                400,
                detail="No departments found. Please complete Departments screen first.",
            )

        return {
            "plant_id": plant_id,
            "departments": [
                {
                    "department_id": dept.department_id,
                    "department_name": dept.department_name,
                }
                for dept in departments
            ],
        }
    finally:
        tenant_db.close()


@router.get("/lines")
async def get_lines_list(
    plant_id: str,
    department_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get list of production lines for a department (for Screen 4 dropdown)"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get lines for this department
        lines = (
            tenant_db.query(ProductionLine)
            .filter(
                ProductionLine.plant_id == plant_id,
                ProductionLine.department_id == department_id,
                ProductionLine.is_active == True,
            )
            .all()
        )

        if not lines:
            raise HTTPException(
                400, detail="No production lines found for this department."
            )

        return {
            "plant_id": plant_id,
            "department_id": department_id,
            "lines": [
                {"line_id": line.line_id, "line_name": line.line_name} for line in lines
            ],
        }
    finally:
        tenant_db.close()


@router.get("/models")
async def get_models_list(
    line_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get list of product models for a line (for Screen 4 dropdown)"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get models for this line
        models = (
            tenant_db.query(ProductModel)
            .filter(ProductModel.line_id == line_id, ProductModel.is_active == True)
            .all()
        )

        if not models:
            raise HTTPException(400, detail="No product models found for this line.")

        return {
            "line_id": line_id,
            "models": [
                {
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "model_code": model.model_code,
                }
                for model in models
            ],
        }
    finally:
        tenant_db.close()


@router.post("/screen5-users", status_code=status.HTTP_201_CREATED)
async def setup_users(
    data: UsersSetupRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    """Screen 5: User Setup — Add team members and complete setup (creates or updates users)"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Verify plant exists
        plant = tenant_db.query(Plant).filter(Plant.plant_id == data.plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")

        # Get setup progress
        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == data.plant_id)
            .first()
        )

        if not progress:
            raise HTTPException(404, detail="Setup progress not found")

        # Verify at least one user
        if len(data.users) == 0:
            raise HTTPException(400, detail="At least one user required")

        created_or_updated_users = []

        for user_data in data.users:
            # Check if user already exists
            full_phone = f"{user_data.phone_country_code}{user_data.phone_number}"
            existing_user = (
                tenant_db.query(User).filter(User.phone_number == full_phone).first()
            )

            # Verify shift exists
            shift = (
                tenant_db.query(Shift)
                .filter(
                    Shift.shift_id == user_data.shift_id,
                    Shift.plant_id == data.plant_id,
                )
                .first()
            )

            if not shift:
                raise HTTPException(
                    400, detail=f"Shift {user_data.shift_id} not found for this plant"
                )

            full_name = f"{user_data.first_name} {user_data.last_name}"

            if existing_user:
                # UPDATE existing user
                existing_user.first_name = user_data.first_name
                existing_user.last_name = user_data.last_name
                existing_user.full_name = full_name
                existing_user.email = user_data.email
                existing_user.default_shift_id = user_data.shift_id
                user_id = existing_user.user_id
                pin_sent = False  # Don't resend PIN for existing users
            else:
                # CREATE new user
                pin = _generate_pin()
                pin_hash = _hash_pin(pin)

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
                    is_active=True,
                )
                tenant_db.add(new_user)
                tenant_db.flush()
                user_id = new_user.user_id

                # Send welcome notification with PIN for new users
                try:
                    await _send_user_welcome_notification(
                        user_data.phone_country_code,
                        user_data.phone_number,
                        user_data.email,
                        user_data.first_name,
                        pin,
                    )
                    pin_sent = True
                except Exception as e:
                    print(f"[USER SETUP] Failed to send notification: {e}")
                    pin_sent = False

            # Update or create plant membership with role
            role = (
                PlantRole.MANAGER if user_data.role == "manager" else PlantRole.MEMBER
            )
            membership = (
                tenant_db.query(PlantMembership)
                .filter(
                    PlantMembership.plant_id == data.plant_id,
                    PlantMembership.user_id == user_id,
                )
                .first()
            )

            if membership:
                # Update existing membership
                membership.role = role
                membership.is_active = True
            else:
                # Create new membership
                membership = PlantMembership(
                    plant_id=data.plant_id,
                    user_id=user_id,
                    role=role,
                    invited_by=current_admin.id,
                    accepted_at=None,  # Will accept when they first login
                    is_active=True,
                )
                tenant_db.add(membership)

            # Update or create offsite access grant
            offsite_grant = (
                tenant_db.query(OffsiteAccessGrant)
                .filter(
                    OffsiteAccessGrant.plant_id == data.plant_id,
                    OffsiteAccessGrant.user_id == user_id,
                )
                .first()
            )

            if user_data.offsite_permission:
                if not offsite_grant:
                    # Create new grant
                    offsite_grant = OffsiteAccessGrant(
                        plant_id=data.plant_id,
                        user_id=user_id,
                        granted_by=current_admin.id,
                        is_active=True,
                    )
                    tenant_db.add(offsite_grant)
                else:
                    # Ensure it's active
                    offsite_grant.is_active = True
            else:
                if offsite_grant:
                    # Revoke offsite access
                    offsite_grant.is_active = False

            created_or_updated_users.append(
                {
                    "user_id": user_id,
                    "full_name": full_name,
                    "phone": full_phone,
                    "email": user_data.email,
                    "role": user_data.role,
                    "shift_id": user_data.shift_id,
                    "offsite_permission": user_data.offsite_permission,
                    "pin_sent": pin_sent,
                }
            )

        # Mark user setup as completed
        progress.users_completed = True
        progress.setup_completed = True
        progress.current_step = SetupStep.COMPLETED
        progress.completed_at = datetime.utcnow()

        tenant_db.commit()

        return {
            "message": "Users created/updated successfully! Setup completed.",
            "users_processed": len(created_or_updated_users),
            "users": created_or_updated_users,
            "setup_completed": True,
            "redirect_to": "dashboard",
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

        progress = (
            tenant_db.query(SetupProgress)
            .filter(SetupProgress.plant_id == plant_id)
            .first()
        )

        if not progress:
            raise HTTPException(404, detail="Setup progress not found")

        # Verify at least one station exists
        station_count = (
            tenant_db.query(Station).filter(Station.plant_id == plant_id).count()
        )

        if station_count == 0:
            raise HTTPException(
                400, detail="At least one station required to complete setup"
            )

        progress.stations_completed = True
        progress.setup_completed = True
        progress.current_step = SetupStep.COMPLETED
        progress.completed_at = datetime.utcnow()
        tenant_db.commit()

        return {
            "message": "Setup completed successfully!",
            "setup_completed": True,
            "redirect_to": "dashboard",
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


# ==================== GET Endpoints for State Restoration ====================


@router.get("/screen1-plant")
async def get_plant_setup_data(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get saved plant setup data for restoration"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get plant
        plant = tenant_db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(404, detail="Plant not found")

        # Get company name
        company = (
            db.query(Company)
            .filter(Company.company_id == current_admin.company_id)
            .first()
        )

        # Get shifts
        shifts = (
            tenant_db.query(Shift)
            .filter(Shift.plant_id == plant_id)
            .order_by(Shift.start_time)
            .all()
        )

        return {
            "company_name": company.company_name if company else "",
            "plant_name": plant.plant_name,
            "address": plant.address,
            "shifts": [
                {
                    "start_time": _format_time(shift.start_time),
                    "end_time": _format_time(shift.end_time),
                    "shift_name": shift.shift_name,
                }
                for shift in shifts
            ],
        }
    finally:
        tenant_db.close()


@router.get("/screen2-departments")
async def get_departments_data(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get saved departments for restoration"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get departments
        departments = (
            tenant_db.query(Department)
            .filter(Department.plant_id == plant_id, Department.is_active == True)
            .all()
        )

        return {
            "departments": [
                {
                    "department_id": dept.department_id,
                    "department_name": dept.department_name,
                }
                for dept in departments
            ]
        }
    finally:
        tenant_db.close()


@router.get("/screen3-lines-models")
async def get_lines_models_data(
    plant_id: str,
    department_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get saved production lines and models for restoration"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get lines for this department
        lines = (
            tenant_db.query(ProductionLine)
            .filter(
                ProductionLine.plant_id == plant_id,
                ProductionLine.department_id == department_id,
                ProductionLine.is_active == True,
            )
            .all()
        )

        lines_data = []
        for line in lines:
            # Get models for this line
            models = (
                tenant_db.query(ProductModel)
                .filter(
                    ProductModel.line_id == line.line_id, ProductModel.is_active == True
                )
                .all()
            )

            lines_data.append(
                {
                    "line_id": line.line_id,
                    "line_name": line.line_name,
                    "models": [
                        {
                            "model_id": model.model_id,
                            "model_name": model.model_name,
                            "model_code": model.model_code,
                        }
                        for model in models
                    ],
                }
            )

        return {"department_id": department_id, "lines": lines_data}
    finally:
        tenant_db.close()


@router.get("/screen4-stations")
async def get_stations_data(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get all stations for this plant"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get all stations
        stations = (
            tenant_db.query(Station)
            .filter(
                Station.plant_id == plant_id, Station.operational_status == "active"
            )
            .all()
        )

        stations_data = []
        for station in stations:
            # Get characteristics
            characteristics = (
                tenant_db.query(Characteristic)
                .filter(
                    Characteristic.station_id == station.station_id,
                    Characteristic.is_active == True,
                )
                .all()
            )

            stations_data.append(
                {
                    "station_id": station.station_id,
                    "station_name": station.station_name,
                    "department_id": station.department_id,
                    "line_id": station.line_id,
                    "sampling_frequency_minutes": station.sampling_frequency_minutes,
                    "characteristics": [
                        {
                            "characteristic_id": char.characteristic_id,
                            "characteristic_name": char.characteristic_name,
                            "unit_of_measure": char.unit_of_measure,
                            "target_value": char.target_value,
                            "usl": char.usl,
                            "lsl": char.lsl,
                            "ucl": char.ucl,
                            "lcl": char.lcl,
                            "sample_size": char.sample_size,
                            "check_frequency_minutes": char.check_frequency_minutes,
                            "chart_type": (
                                char.chart_type.value if char.chart_type else None
                            ),
                        }
                        for char in characteristics
                    ],
                }
            )

        return {"plant_id": plant_id, "stations": stations_data}
    finally:
        tenant_db.close()


@router.get("/screen5-users")
async def get_users_data(
    plant_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """Get all users for this plant"""
    tenant_db = _get_tenant_db(current_admin)

    try:
        tenant_db = _ensure_tenant_schema(current_admin, tenant_db)

        # Get all plant memberships
        memberships = (
            tenant_db.query(PlantMembership)
            .filter(
                PlantMembership.plant_id == plant_id, PlantMembership.is_active == True
            )
            .all()
        )

        users_data = []
        for membership in memberships:
            user = (
                tenant_db.query(User).filter(User.user_id == membership.user_id).first()
            )

            if user:
                # Check offsite access
                offsite_grant = (
                    tenant_db.query(OffsiteAccessGrant)
                    .filter(
                        OffsiteAccessGrant.plant_id == plant_id,
                        OffsiteAccessGrant.user_id == user.user_id,
                        OffsiteAccessGrant.is_active == True,
                    )
                    .first()
                )

                users_data.append(
                    {
                        "user_id": user.user_id,
                        "role": membership.role.value,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "phone_country_code": user.phone_country_code,
                        "phone_number": user.phone_number.replace(
                            user.phone_country_code, ""
                        ),
                        "email": user.email,
                        "shift_id": user.default_shift_id,
                        "offsite_permission": offsite_grant is not None,
                    }
                )

        return {"plant_id": plant_id, "users": users_data}
    finally:
        tenant_db.close()
        tenant_db.close()
