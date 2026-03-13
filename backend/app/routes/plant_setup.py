"""Consolidated Plant Setup — Manage Company, Plant, and Shifts"""

from datetime import datetime, time
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db, get_tenant_db
from app.models.admin import Admin
from app.models.company import Company
from app.models.tenant.department import Department
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.product_model import ProductModel
from app.models.tenant.station import Station
from app.models.tenant.characteristic import Characteristic, ChartType
from app.models.tenant.plant import Plant
from app.models.tenant.shift import Shift
from app.routes.users_auth import get_current_user

router = APIRouter(prefix="/api/v1/plant-setup", tags=["Plant Setup"])


# ==================== SCHEMAS ====================


class ShiftSyncItem(BaseModel):
    shift_id: Optional[str] = Field(None, description="UUID of existing shift. Leave null for new shift.")
    shift_name: Optional[str] = None
    start_time: str = Field(..., description="HH:MM AM/PM format")
    end_time: str = Field(..., description="HH:MM AM/PM format")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%I:%M %p")
            return v
        except ValueError:
            raise ValueError("Time must be in HH:MM AM/PM format")


class PlantDetailsResponse(BaseModel):
    company_name: str
    plant_name: str
    address: str
    shifts: List[ShiftSyncItem]


class PlantDetailsUpdate(BaseModel):
    company_name: Optional[str] = None
    plant_name: Optional[str] = None
    address: Optional[str] = None
    shifts: Optional[List[ShiftSyncItem]] = None


# --- Hierarchy Schemas ---

class CharacteristicItem(BaseModel):
    characteristic_id: str
    characteristic_name: str
    lsl: Optional[float] = None
    usl: Optional[float] = None
    target_value: Optional[float] = None
    unit_of_measure: Optional[str] = None


class StationItem(BaseModel):
    station_id: str
    station_name: str
    characteristics: List[CharacteristicItem]


class LineItem(BaseModel):
    line_id: str
    line_name: str
    model_ids: List[str]  # Just the codes/names as shown in Figma
    stations: List[StationItem]
    station_count: int


class DepartmentItem(BaseModel):
    department_id: str
    department_name: str
    lines: List[LineItem]
    line_count: int
    station_count: int
    model_count: int


# --- Sync Update Schemas ---

class DepartmentSyncItem(BaseModel):
    department_id: Optional[str] = None
    department_name: str


class DepartmentsSyncRequest(BaseModel):
    departments: List[DepartmentSyncItem]


class ModelSyncItem(BaseModel):
    model_id: Optional[str] = None
    model_name: str
    model_code: str


class LineSyncRequest(BaseModel):
    line_id: str
    line_name: str
    models: List[ModelSyncItem]


class LineCreateRequest(BaseModel):
    line_name: str
    department_id: Optional[str] = None
    models: List[ModelSyncItem]



class CharacteristicSyncItem(BaseModel):
    characteristic_id: Optional[str] = None
    characteristic_name: str
    lsl: Optional[float] = None
    usl: Optional[float] = None
    unit_of_measure: Optional[str] = None


class StationSyncRequest(BaseModel):
    station_id: str
    station_name: str
    department_id: Optional[str] = None
    line_id: Optional[str] = None
    characteristics: List[CharacteristicSyncItem]


class StationCreateRequest(BaseModel):
    station_name: str
    department_id: Optional[str] = None
    line_id: Optional[str] = None
    characteristics: List[CharacteristicSyncItem]



# ==================== HELPERS ====================


def _parse_time(time_str: str) -> time:
    """Convert '08:00 AM' to time object"""
    return datetime.strptime(time_str, "%I:%M %p").time()


def _format_time(time_obj: time) -> str:
    """Convert time object to '08:00 AM'"""
    return datetime.combine(datetime.today(), time_obj).strftime("%I:%M %p")


# ==================== ENDPOINTS ====================


@router.get("/plant-details", response_model=PlantDetailsResponse)
async def get_plant_details(
    current: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get consolidated Plant details for the current user's company.
    Works for both Admin and Invitee.
    """
    company_id = current["company_id"]
    
    # 1. Get Company from Public Schema
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 2. Get Plant and Shifts from Tenant Schema
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        if not plant:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        shifts = tenant_db.query(Shift).filter(Shift.plant_id == plant.plant_id).order_by(Shift.start_time).all()
        
        return {
            "company_name": company.company_name,
            "plant_name": plant.plant_name,
            "address": plant.address or "",
            "shifts": [
                {
                    "shift_id": s.shift_id,
                    "shift_name": s.shift_name,
                    "start_time": _format_time(s.start_time),
                    "end_time": _format_time(s.end_time)
                } for s in shifts
            ]
        }
    finally:
        tenant_db.close()


@router.get("/departments", response_model=List[dict])
async def list_departments(
    current: dict = Depends(get_current_user)
):
    """List all departments for dropdowns."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        depts = tenant_db.query(Department).filter(Department.is_active == True).all()
        return [{"department_id": d.department_id, "department_name": d.department_name} for d in depts]
    finally:
        tenant_db.close()


@router.get("/lines", response_model=List[dict])
async def list_lines(
    current: dict = Depends(get_current_user)
):
    """List all production lines for dropdowns."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        lines = tenant_db.query(ProductionLine).filter(ProductionLine.is_active == True).all()
        return [{"line_id": l.line_id, "line_name": l.line_name, "department_id": l.department_id} for l in lines]
    finally:
        tenant_db.close()


@router.get("/models", response_model=List[dict])
async def list_models(
    current: dict = Depends(get_current_user)
):
    """List all product models."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        models = tenant_db.query(ProductModel).filter(ProductModel.is_active == True).all()
        return [{"model_id": m.model_id, "model_name": m.model_name, "model_code": m.model_code, "line_id": m.line_id} for m in models]
    finally:
        tenant_db.close()


@router.get("/stations/{station_id}", response_model=dict)
async def get_station_details(
    station_id: str,
    current: dict = Depends(get_current_user)
):
    """Detailed view of a station for editing."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        station = tenant_db.query(Station).filter(Station.station_id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        chars = tenant_db.query(Characteristic).filter(Characteristic.station_id == station_id, Characteristic.is_active == True).all()
        
        return {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "department_id": station.department_id,
            "line_id": station.line_id,
            "characteristics": [
                {
                    "characteristic_id": c.characteristic_id,
                    "characteristic_name": c.characteristic_name,
                    "lsl": float(c.lsl) if c.lsl is not None else None,
                    "usl": float(c.usl) if c.usl is not None else None,
                    "unit_of_measure": c.unit_of_measure
                } for c in chars
            ]
        }
    finally:
        tenant_db.close()


@router.patch("/plant-details", status_code=status.HTTP_200_OK)
async def update_plant_details(
    data: PlantDetailsUpdate,
    current: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update Plant details and Sync Shifts.
    Restricted to Admins or Invitee Managers (TODO: check manager role if needed).
    """
    # For now, we only allow role 'admin' or 'invitee' (if they have the token, we trust them)
    # If a finer check is needed, we'd check current["role"] here.
    
    company_id = current["company_id"]
    
    # 1. Update Company (Public Schema)
    if data.company_name:
        company = db.query(Company).filter(Company.company_id == company_id).first()
        if company:
            company.company_name = data.company_name
            db.commit()

    # 2. Update Plant & Sync Shifts (Tenant Schema)
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        if not plant:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        if data.plant_name:
            plant.plant_name = data.plant_name
        if data.address is not None:
            plant.address = data.address
            
        # --- Shift Sync Logic (Upsert + Delete) ---
        if data.shifts is not None:
            # Get existing shifts to compare
            existing_shifts = tenant_db.query(Shift).filter(Shift.plant_id == plant.plant_id).all()
            existing_shift_ids = {s.shift_id for s in existing_shifts}

            # B. Upsert (Update existing + Insert new)

            for s_data in data.shifts:
                if s_data.shift_id and s_data.shift_id in existing_shift_ids:
                    # UPDATE
                    s_obj = next(s for s in existing_shifts if s.shift_id == s_data.shift_id)
                    s_obj.shift_name = s_data.shift_name
                    s_obj.start_time = _parse_time(s_data.start_time)
                    s_obj.end_time = _parse_time(s_data.end_time)
                    s_obj.updated_at = datetime.utcnow()
                else:
                    # INSERT (new shift)
                    new_shift = Shift(
                        shift_id=str(uuid.uuid4()),
                        plant_id=plant.plant_id,
                        shift_name=s_data.shift_name,
                        start_time=_parse_time(s_data.start_time),
                        end_time=_parse_time(s_data.end_time)
                    )
                    tenant_db.add(new_shift)

        tenant_db.commit()
        return {"message": "Plant details and shifts updated successfully"}
    except Exception as e:
        tenant_db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        tenant_db.close()


@router.delete("/shifts/{shift_id}", status_code=status.HTTP_200_OK)
async def delete_shift(
    shift_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a shift."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        shift = tenant_db.query(Shift).filter(Shift.shift_id == shift_id).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        tenant_db.delete(shift)
        tenant_db.commit()
        return {"message": "Shift deleted successfully"}
    finally:
        tenant_db.close()



@router.get("/station-hierarchy", response_model=List[DepartmentItem])
async def get_station_hierarchy(
    current: dict = Depends(get_current_user)
):
    """
    Returns the nested hierarchy: Departments -> Lines -> Stations -> Characteristics.
    Includes summary counts for the mobile app headers.
    """
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    
    try:
        # Fetch everything in the hierarchy (Active only)
        depts = tenant_db.query(Department).filter(Department.is_active == True).all()
        lines = tenant_db.query(ProductionLine).filter(ProductionLine.is_active == True).all()
        models = tenant_db.query(ProductModel).filter(ProductModel.line_id != None, ProductModel.is_active == True).all()
        stations = tenant_db.query(Station).filter(Station.operational_status == "active").all()
        chars = tenant_db.query(Characteristic).filter(Characteristic.is_active == True).all()

        hierarchy = []
        for d in depts:
            d_lines = [l for l in lines if l.department_id == d.department_id]
            line_items = []
            d_station_total = 0
            d_model_set = set()

            for l in d_lines:
                l_models = [m for m in models if m.line_id == l.line_id]
                l_stations = [s for s in stations if s.line_id == l.line_id]
                
                # Add models to department unique set
                for m in l_models:
                    d_model_set.add(m.model_id)
                
                station_items = []
                for s in l_stations:
                    s_chars = [c for c in chars if c.station_id == s.station_id]
                    station_items.append({
                        "station_id": s.station_id,
                        "station_name": s.station_name,
                        "characteristics": [
                            {
                                "characteristic_id": c.characteristic_id,
                                "characteristic_name": c.characteristic_name,
                                "lsl": float(c.lsl) if c.lsl is not None else None,
                                "usl": float(c.usl) if c.usl is not None else None,
                                "target_value": float(c.target_value) if c.target_value is not None else None,
                                "unit_of_measure": c.unit_of_measure
                            } for c in s_chars
                        ]
                    })
                
                d_station_total += len(l_stations)
                
                line_items.append({
                    "line_id": l.line_id,
                    "line_name": l.line_name,
                    "model_ids": [m.model_code for m in l_models],
                    "stations": station_items,
                    "station_count": len(l_stations)
                })

            hierarchy.append({
                "department_id": d.department_id,
                "department_name": d.department_name,
                "lines": line_items,
                "line_count": len(d_lines),
                "station_count": d_station_total,
                "model_count": len(d_model_set)
            })

        return hierarchy
    finally:
        tenant_db.close()


@router.patch("/departments-sync", status_code=status.HTTP_200_OK)
async def sync_departments(
    data: DepartmentsSyncRequest,
    current: dict = Depends(get_current_user)
):
    """Sync departments (Upsert + Delete)."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        if not plant:
             raise HTTPException(status_code=404, detail="Plant not found")

        existing = tenant_db.query(Department).filter(Department.plant_id == plant.plant_id).all()
        existing_ids = {d.department_id for d in existing}
        incoming_ids = {d.department_id for d in data.departments if d.department_id}

        # Upsert
        for d_data in data.departments:
            if d_data.department_id and d_data.department_id in existing_ids:
                d_obj = next(d for d in existing if d.department_id == d_data.department_id)
                d_obj.department_name = d_data.department_name
            else:
                new_dept = Department(
                    department_id=str(uuid.uuid4()),
                    plant_id=plant.plant_id,
                    department_name=d_data.department_name
                )
                tenant_db.add(new_dept)
        
        tenant_db.commit()
        return {"message": "Departments updated successfully"}
    finally:
        tenant_db.close()


@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentSyncItem,
    current: dict = Depends(get_current_user)
):
    """Explicitly create a new department."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        if not plant:
             raise HTTPException(status_code=404, detail="Plant not found")

        new_dept = Department(
            department_id=str(uuid.uuid4()),
            plant_id=plant.plant_id,
            department_name=data.department_name
        )
        tenant_db.add(new_dept)
        tenant_db.commit()
        return {"message": "Department created successfully", "department_id": new_dept.department_id}
    finally:
        tenant_db.close()



@router.delete("/departments/{department_id}", status_code=status.HTTP_200_OK)
async def delete_department(
    department_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a department."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        dept = tenant_db.query(Department).filter(Department.department_id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        tenant_db.delete(dept)
        tenant_db.commit()
        return {"message": "Department deleted successfully"}
    finally:
        tenant_db.close()



@router.patch("/line-sync", status_code=status.HTTP_200_OK)
async def sync_line_and_models(
    data: LineSyncRequest,
    current: dict = Depends(get_current_user)
):
    """Sync a specific line and its models (Upsert + Delete)."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        line = tenant_db.query(ProductionLine).filter(ProductionLine.line_id == data.line_id).first()
        if not line:
             raise HTTPException(status_code=404, detail="Line not found")

        line.line_name = data.line_name
        
        # Sync Models
        existing_models = tenant_db.query(ProductModel).filter(ProductModel.line_id == line.line_id).all()
        existing_ids = {m.model_id for m in existing_models}
        incoming_ids = {m.model_id for m in data.models if m.model_id}

        # Upsert
        for m_data in data.models:
            if m_data.model_id and m_data.model_id in existing_ids:
                m_obj = next(m for m in existing_models if m.model_id == m_data.model_id)
                m_obj.model_name = m_data.model_name
                m_obj.model_code = m_data.model_code
            else:
                new_model = ProductModel(
                    model_id=str(uuid.uuid4()),
                    line_id=line.line_id,
                    model_name=m_data.model_name,
                    model_code=m_data.model_code
                )
                tenant_db.add(new_model)

        tenant_db.commit()
        return {"message": "Line and models updated successfully"}
    finally:
        tenant_db.close()


@router.post("/lines", status_code=status.HTTP_201_CREATED)
async def create_line(
    data: LineCreateRequest,
    current: dict = Depends(get_current_user)
):
    """Explicitly create a new line with models."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        new_line = ProductionLine(
            line_id=str(uuid.uuid4()),
            line_name=data.line_name,
            department_id=data.department_id,
            is_active=True
        )
        tenant_db.add(new_line)
        tenant_db.flush()

        for m_data in data.models:
            new_model = ProductModel(
                model_id=str(uuid.uuid4()),
                line_id=new_line.line_id,
                model_name=m_data.model_name,
                model_code=m_data.model_code
            )
            tenant_db.add(new_model)

        tenant_db.commit()
        return {"message": "Line created successfully", "line_id": new_line.line_id}
    finally:
        tenant_db.close()



@router.delete("/lines/{line_id}", status_code=status.HTTP_200_OK)
async def delete_line(
    line_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a line."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        line = tenant_db.query(ProductionLine).filter(ProductionLine.line_id == line_id).first()
        if not line:
            raise HTTPException(status_code=404, detail="Line not found")
        tenant_db.delete(line)
        tenant_db.commit()
        return {"message": "Line deleted successfully"}
    finally:
        tenant_db.close()


@router.delete("/models/{model_id}", status_code=status.HTTP_200_OK)
async def delete_model(
    model_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a model."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        model = tenant_db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        tenant_db.delete(model)
        tenant_db.commit()
        return {"message": "Model deleted successfully"}
    finally:
        tenant_db.close()



@router.post("/stations", status_code=status.HTTP_201_CREATED)
async def create_station(
    data: StationCreateRequest,
    current: dict = Depends(get_current_user)
):
    """Create a new station with its characteristics."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        plant = tenant_db.query(Plant).filter(Plant.is_active == True).first()
        if not plant:
             raise HTTPException(status_code=404, detail="Plant not found")

        new_station = Station(
            station_id=str(uuid.uuid4()),
            plant_id=plant.plant_id,
            station_name=data.station_name,
            department_id=data.department_id,
            line_id=data.line_id,
            operational_status="active"
        )
        tenant_db.add(new_station)
        tenant_db.flush() # Get station_id for characteristics

        for c_data in data.characteristics:
            new_char = Characteristic(
                characteristic_id=str(uuid.uuid4()),
                station_id=new_station.station_id,
                characteristic_name=c_data.characteristic_name,
                lsl=c_data.lsl,
                usl=c_data.usl,
                unit_of_measure=c_data.unit_of_measure,
                chart_type=ChartType.I_MR
            )
            tenant_db.add(new_char)

        tenant_db.commit()
        return {"message": "Station created successfully", "station_id": new_station.station_id}
    finally:
        tenant_db.close()


@router.patch("/station-sync", status_code=status.HTTP_200_OK)
async def sync_station_and_characteristics(
    data: StationSyncRequest,
    current: dict = Depends(get_current_user)
):
    """Sync a specific station and its characteristics (Upsert + Delete)."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        station = tenant_db.query(Station).filter(Station.station_id == data.station_id).first()
        if not station:
             raise HTTPException(status_code=404, detail="Station not found")

        station.station_name = data.station_name
        station.department_id = data.department_id
        station.line_id = data.line_id
        
        # Sync Characteristics
        existing_chars = tenant_db.query(Characteristic).filter(Characteristic.station_id == station.station_id).all()
        existing_ids = {c.characteristic_id for c in existing_chars}
        incoming_ids = {c.characteristic_id for c in data.characteristics if c.characteristic_id}

        # Upsert
        for c_data in data.characteristics:
            if c_data.characteristic_id and c_data.characteristic_id in existing_ids:
                c_obj = next(c for c in existing_chars if c.characteristic_id == c_data.characteristic_id)
                c_obj.characteristic_name = c_data.characteristic_name
                c_obj.lsl = c_data.lsl
                c_obj.usl = c_data.usl
                c_obj.unit_of_measure = c_data.unit_of_measure
                c_obj.updated_at = datetime.utcnow()
            else:
                new_char = Characteristic(
                    characteristic_id=str(uuid.uuid4()),
                    station_id=station.station_id,
                    characteristic_name=c_data.characteristic_name,
                    lsl=c_data.lsl,
                    usl=c_data.usl,
                    unit_of_measure=c_data.unit_of_measure,
                    chart_type=ChartType.I_MR # default
                )
                tenant_db.add(new_char)

        tenant_db.commit()
        return {"message": "Station and characteristics updated successfully"}
    finally:
        tenant_db.close()


@router.delete("/stations/{station_id}", status_code=status.HTTP_200_OK)
async def delete_station(
    station_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a station."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        station = tenant_db.query(Station).filter(Station.station_id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        tenant_db.delete(station)
        tenant_db.commit()
        return {"message": "Station deleted successfully"}
    finally:
        tenant_db.close()


@router.delete("/characteristics/{characteristic_id}", status_code=status.HTTP_200_OK)
async def delete_characteristic(
    characteristic_id: str,
    current: dict = Depends(get_current_user)
):
    """Explicitly delete a characteristic."""
    company_id = current["company_id"]
    tenant_db_gen = get_tenant_db(company_id)
    tenant_db: Session = next(tenant_db_gen)
    try:
        char = tenant_db.query(Characteristic).filter(Characteristic.characteristic_id == characteristic_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Characteristic not found")
        tenant_db.delete(char)
        tenant_db.commit()
        return {"message": "Characteristic deleted successfully"}
    finally:
        tenant_db.close()


