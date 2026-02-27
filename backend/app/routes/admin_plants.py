"""Admin — Plant management routes"""

from app.routes.auth import get_current_admin
from app.database import get_tenant_db
from app.models.admin import Admin
from app.models.tenant.plant import Plant
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/plants", tags=["Admin — Plants"])


class CreatePlantRequest(BaseModel):
    plant_name: str
    plant_code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: int = 100
    timezone: Optional[str] = None


class UpdatePlantRequest(BaseModel):
    plant_name: Optional[str] = None
    plant_code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


def _get_tenant_db(admin: Admin) -> Session:
    gen = get_tenant_db(admin.company_id)
    return next(gen)


@router.get("/", status_code=status.HTTP_200_OK)
async def list_plants(current_admin: Admin = Depends(get_current_admin)):
    """List all plants for the current admin's company."""
    db = _get_tenant_db(current_admin)
    try:
        plants = db.query(Plant).all()
        return {
            "plants": [
                {
                    "plant_id": p.plant_id,
                    "plant_name": p.plant_name,
                    "plant_code": p.plant_code,
                    "city": p.city,
                    "country": p.country,
                    "is_active": p.is_active,
                    "entitlement_active": p.entitlement_active,
                    "created_at": p.created_at.isoformat(),
                }
                for p in plants
            ]
        }
    finally:
        db.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_plant(
    data: CreatePlantRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    """Create a new plant for the current admin's company."""
    db = _get_tenant_db(current_admin)
    try:
        plant = Plant(
            plant_name=data.plant_name,
            plant_code=data.plant_code,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country,
            postal_code=data.postal_code,
            latitude=data.latitude,
            longitude=data.longitude,
            geofence_radius_meters=data.geofence_radius_meters,
            timezone=data.timezone,
            is_active=True,
            entitlement_active=False,
        )
        db.add(plant)
        db.commit()
        db.refresh(plant)
        return {
            "message": "Plant created successfully",
            "plant_id": plant.plant_id,
            "plant_name": plant.plant_name,
        }
    finally:
        db.close()


@router.get("/{plant_id}", status_code=status.HTTP_200_OK)
async def get_plant(
    plant_id: str, current_admin: Admin = Depends(get_current_admin)
):
    """Get a plant by ID."""
    db = _get_tenant_db(current_admin)
    try:
        plant = db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found"
            )
        return plant
    finally:
        db.close()


@router.patch("/{plant_id}", status_code=status.HTTP_200_OK)
async def update_plant(
    plant_id: str,
    data: UpdatePlantRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    """Update plant details."""
    db = _get_tenant_db(current_admin)
    try:
        plant = db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found"
            )
        for field, value in data.dict(exclude_none=True).items():
            setattr(plant, field, value)
        plant.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "Plant updated successfully", "plant_id": plant.plant_id}
    finally:
        db.close()


@router.delete("/{plant_id}", status_code=status.HTTP_200_OK)
async def delete_plant(
    plant_id: str, current_admin: Admin = Depends(get_current_admin)
):
    """Soft-delete (deactivate) a plant."""
    db = _get_tenant_db(current_admin)
    try:
        plant = db.query(Plant).filter(Plant.plant_id == plant_id).first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found"
            )
        plant.is_active = False
        plant.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "Plant deactivated successfully"}
    finally:
        db.close()
