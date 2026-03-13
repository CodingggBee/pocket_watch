"""Mobile Data Entry API endpoints for plant workers."""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_tenant_db
from app.routes.users_auth import get_current_user

from app.models.tenant.station import Station, OperationalStatus
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.product_model import ProductModel
from app.models.tenant.characteristic import Characteristic
from app.models.tenant.sample import Sample
from app.models.tenant.measurement import Measurement
# from app.models.tenant.violation import Violation, ViolationType, Severity, ViolationStatus # Future integration

router = APIRouter(prefix="/data-entry", tags=["Data Entry"])

def _tenant_db(current_user: dict) -> Session:
    company_id = current_user["company_id"]
    db_gen = get_tenant_db(company_id)
    return next(db_gen)


@router.get("/stations")
def get_station_statuses(
    plant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a list of all lines and their stations for a given plant,
    annotated with the frontend status badges: "Missed check", 
    "Incomplete data", or "Complete data".
    """
    db = _tenant_db(current_user)
    try:
        # Get all lines and stations for the plant
        lines = db.query(ProductionLine).filter(ProductionLine.plant_id == plant_id, ProductionLine.is_active == True).all()
        stations = db.query(Station).filter(Station.plant_id == plant_id, Station.operational_status == OperationalStatus.ACTIVE).all()
        characteristics = db.query(Characteristic).filter(Characteristic.is_active == True).all()
        
        # Organize characteristics by station_id for fast lookup
        station_chars = {}
        for c in characteristics:
            if c.station_id not in station_chars:
                station_chars[c.station_id] = []
            station_chars[c.station_id].append(c)

        result = []
        for line in lines:
            line_data = {
                "line_id": line.line_id,
                "line_name": line.line_name,
                "stations": []
            }
            line_stations = [s for s in stations if s.line_id == line.line_id]
            
            for station in line_stations:
                chars = station_chars.get(station.station_id, [])
                
                status_flag = "Complete data"
                
                if not chars:
                    status_flag = "Complete data" # No checks required
                else:
                    now = datetime.utcnow()
                    has_missing = False
                    
                    for char in chars:
                        freq_minutes = char.check_frequency_minutes or 60 # Defaulting to 60 if null
                        
                        # Find the last time data was submitted for this characteristic
                        last_sample = (
                            db.query(Sample)
                            .filter(Sample.characteristic_id == char.characteristic_id)
                            .order_by(desc(Sample.sample_datetime))
                            .first()
                        )
                        
                        if not last_sample:
                            has_missing = True # Never checked
                        else:
                            time_since_check = now - last_sample.sample_datetime
                            if time_since_check > timedelta(minutes=freq_minutes):
                                has_missing = True
                    
                    if has_missing:
                        status_flag = "Missed check"
                    # Note: "Incomplete data" logic can be added here in the future 
                    # if we track partial drafts, but for now it's either Missed or Complete.

                line_data["stations"].append({
                    "station_id": station.station_id,
                    "station_name": station.station_name,
                    "status": status_flag
                })
            
            result.append(line_data)
            
        return result
    finally:
        db.close()


@router.get("/stations/{station_id}/init")
def get_station_entry_init(
    station_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the specific models and characteristics for a station 
    to initialize the data entry screen on the mobile app.
    """
    db = _tenant_db(current_user)
    try:
        station = db.query(Station).filter(Station.station_id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # 1. Fetch Models assigned to this station
        models_data = []
        if station.model_ids:
            models = db.query(ProductModel).filter(ProductModel.model_id.in_(station.model_ids)).all()
            models_data = [
                {
                    "model_id": m.model_id,
                    "model_name": m.model_name,
                    "model_code": m.model_code
                } for m in models
            ]
        
        # 2. Fetch Characteristics for this station
        chars = db.query(Characteristic).filter(
            Characteristic.station_id == station_id, 
            Characteristic.is_active == True
        ).all()
        
        chars_data = [
            {
                "characteristic_id": c.characteristic_id,
                "characteristic_name": c.characteristic_name,
                "unit": c.unit_of_measure,
                "lsl": float(c.lsl) if c.lsl else None,
                "usl": float(c.usl) if c.usl else None,
                "target": float(c.target_value) if c.target_value else None,
                "sample_size": c.sample_size or 1,
                "frequency": c.check_frequency_minutes or 60,
                "chart_type": c.chart_type.value if hasattr(c.chart_type, 'value') else str(c.chart_type)
            } for c in chars
        ]

        return {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "models": models_data,
            "characteristics": chars_data
        }
    finally:
        db.close()


# ── POST Payload definition ──

class CharacteristicInput(BaseModel):
    characteristic_id: str
    measurements: List[float]

class DataEntrySubmit(BaseModel):
    station_id: str
    model_id: str
    characteristics: List[CharacteristicInput]

@router.post("/submit")
def submit_data_entry(
    payload: DataEntrySubmit,
    current_user: dict = Depends(get_current_user)
):
    """
    Receives frontend measurements arrays, attaches backend context 
    (user_id, plant_id, timestamp), and saves them to the database.
    (This is the trigger point to calculate Out of Spec, Not Capable, etc.)
    """
    db = _tenant_db(current_user)
    try:
        user_id = current_user["user_id"]
        
        # 1. Fetch Station to determine plant_id
        station = db.query(Station).filter(Station.station_id == payload.station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
            
        plant_id = station.plant_id
        submit_time = datetime.utcnow()
        
        # 2. Process each characteristic input
        samples_created = []
        for char_input in payload.characteristics:
            # Create a single Sample row summarizing this check
            new_sample = Sample(
                characteristic_id=char_input.characteristic_id,
                station_id=payload.station_id,
                user_id=user_id,
                plant_id=plant_id,
                sample_datetime=submit_time,
            )
            db.add(new_sample)
            db.flush() # Flush to get the new_sample_id immediately
            
            # Create the underlying Measurements for the sample
            for index, val in enumerate(char_input.measurements):
                meas = Measurement(
                    sample_id=new_sample.sample_id,
                    measurement_value=val,
                    measurement_order=index + 1 # Backend automatically extracts measurement_order!
                )
                db.add(meas)
                
            samples_created.append(new_sample.sample_id)
            
            # NOTE: At this precise point, in a future update, we would run 
            # the statistical evaluation for 'Out of Spec', 'Not in Control', 
            # and 'Not Capable' against this sample, and insert records 
            # into the Violation table. 

        db.commit()
        
        return {
            "success": True, 
            "message": "Data saved successfully",
            "samples_created": len(samples_created),
            "sample_datetime": submit_time.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
