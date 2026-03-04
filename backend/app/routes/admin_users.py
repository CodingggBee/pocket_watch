"""Admin — User (plant worker) management routes"""

from app.routes.auth import get_current_admin
from app.database import get_tenant_db
from app.models.admin import Admin
from app.models.tenant.user import User
from app.utils.crypto import hash_password
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/users", tags=["Admin — Users"])


class CreateUserRequest(BaseModel):
    phone_number: str
    phone_country_code: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


def _get_tenant_db(admin: Admin) -> Session:
    gen = get_tenant_db(admin.company_id)
    return next(gen)


@router.get("/", status_code=status.HTTP_200_OK)
async def list_users(current_admin: Admin = Depends(get_current_admin)):
    """List all users (plant workers) in the admin's company tenant."""
    db = _get_tenant_db(current_admin)
    try:
        users = db.query(User).all()
        return {
            "users": [
                {
                    "user_id": u.user_id,
                    "phone_number": u.phone_number,
                    "full_name": u.full_name,
                    "email": u.email,
                    "is_active": u.is_active,
                    "phone_verified": u.phone_verified,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
        }
    finally:
        db.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: CreateUserRequest, current_admin: Admin = Depends(get_current_admin)
):
    """
    Pre-create a plant worker account.
    Worker can then log in via SMS OTP + PIN flow.
    """
    db = _get_tenant_db(current_admin)
    try:
        existing = (
            db.query(User).filter(User.phone_number == data.phone_number).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered",
            )

        user = User(
            phone_number=data.phone_number,
            phone_country_code=data.phone_country_code,
            full_name=data.full_name,
            email=data.email,
            is_active=True,
            phone_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "message": "User created successfully",
            "user_id": user.user_id,
            "phone_number": user.phone_number,
            "company_id": current_admin.company_id,
        }
    finally:
        db.close()


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(user_id: str, current_admin: Admin = Depends(get_current_admin)):
    """Get a user by ID."""
    db = _get_tenant_db(current_admin)
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return {
            "user_id": user.user_id,
            "phone_number": user.phone_number,
            "phone_country_code": user.phone_country_code,
            "full_name": user.full_name,
            "email": user.email,
            "is_active": user.is_active,
            "phone_verified": user.phone_verified,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
        }
    finally:
        db.close()


@router.patch("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(
    user_id: str,
    data: UpdateUserRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    """Update a user's profile."""
    db = _get_tenant_db(current_admin)
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        for field, value in data.dict(exclude_none=True).items():
            setattr(user, field, value)
        user.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "User updated successfully"}
    finally:
        db.close()


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str, current_admin: Admin = Depends(get_current_admin)
):
    """Soft-delete (deactivate) a plant worker."""
    db = _get_tenant_db(current_admin)
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "User deactivated successfully"}
    finally:
        db.close()
