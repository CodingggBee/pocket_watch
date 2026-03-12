"""User (plant worker) authentication routes — multi-tenant schema"""

from datetime import datetime, timedelta
from typing import Optional, Generator

from app.config import get_settings
from app.database import find_company_by_phone, get_tenant_db
from app.models.tenant.user import User
from app.models.tenant.otp_cache import OTPCache
from app.models.tenant.user_session import UserSession
from app.services.sms import send_invitation_otp, send_sms_otp, send_pin_sms
from app.utils.crypto import (
    hash_otp,
    hash_password,
    hash_token,
    verify_otp,
    verify_password,
    verify_token_hash,
)
from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    get_company_id_from_token,
    get_token_expiry,
    verify_access_token,
    verify_refresh_token,
    decode_token
)
from app.utils.otp import generate_numeric_code, generate_otp
from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

settings = get_settings()

router = APIRouter(prefix="/users/auth", tags=["User Authentication"])

# Security scheme — shows the lock/Authorize button in Swagger UI
user_bearer_scheme = HTTPBearer()


# ──────────────────────────────────────────────
# Schemas (inline for conciseness)
# ──────────────────────────────────────────────
class SendOTPRequest(BaseModel):
    phone_number: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str


class LoginPINRequest(BaseModel):
    phone_number: str
    pin: str


class ResetPINRequest(BaseModel):
    phone_number: str
    otp: str
    new_pin: str


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_country_code: Optional[str] = None
    phone_number: Optional[str] = None


# ──────────────────────────────────────────────
# Tenant DB dependency
# ──────────────────────────────────────────────
def _tenant_db(company_id: str) -> Generator[Session, None, None]:
    yield from get_tenant_db(company_id)


# ──────────────────────────────────────────────
# FLOW 1: SEND OTP (phone-only — auto-discovers company)
# ──────────────────────────────────────────────
@router.post("/send-otp", status_code=status.HTTP_200_OK)
async def send_otp(data: SendOTPRequest):
    """
    Send a 6-digit OTP to the user's phone number.
    Only requires phone_number — automatically discovers which company
    the worker belongs to, then sends a well-formatted invitation SMS
    with company and plant details.
    """
    # Auto-discover company from phone number across all tenant schemas
    lookup = find_company_by_phone(data.phone_number)
    if not lookup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found. Please contact your administrator.",
        )
    if not lookup["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive."
        )

    company_id = lookup["company_id"]
    company_name = lookup["company_name"]
    plants = lookup["plants"]

    db_gen = get_tenant_db(company_id)
    db: Session = next(db_gen)
    try:
        otp_code = generate_otp()
        otp_record = OTPCache(
            phone_number=data.phone_number,
            otp_hash=hash_otp(otp_code),
            purpose="VERIFICATION",
            is_used=False,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        db.add(otp_record)
        db.commit()

        # Send well-formatted invitation SMS with company + plant info
        await send_invitation_otp(
            phone_number=data.phone_number,
            otp=otp_code,
            company_name=company_name,
            company_id=company_id,
            plants=plants,
        )
        return {
            "message": "OTP sent successfully",
            "phone_number": data.phone_number,
            "company_id": company_id,
            "company_name": company_name,
        }
    finally:
        db.close()


# ──────────────────────────────────────────────
# FLOW 2: VERIFY OTP → generate + send PIN
# ──────────────────────────────────────────────
@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp_endpoint(data: VerifyOTPRequest):
    """
    Verify the SMS OTP.
    If the user has no PIN yet, generate a 4-digit PIN and send it via SMS.
    Only requires phone_number + otp — company is auto-discovered.
    """
    lookup = find_company_by_phone(data.phone_number)
    if not lookup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found. Please contact your administrator.",
        )

    company_id = lookup["company_id"]
    db_gen = get_tenant_db(company_id)
    db: Session = next(db_gen)
    try:
        otp_record = (
            db.query(OTPCache)
            .filter(
                OTPCache.phone_number == data.phone_number,
                OTPCache.purpose == "VERIFICATION",
                OTPCache.is_used == False,
                OTPCache.expires_at > datetime.utcnow(),
            )
            .order_by(OTPCache.created_at.desc())
            .first()
        )
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
            )
        if not verify_otp(data.otp, otp_record.otp_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect OTP"
            )

        otp_record.is_used = True
        user = db.query(User).filter(User.phone_number == data.phone_number).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.phone_verified = True

        message = "OTP verified successfully."
        if not user.pin_hash:
            # First time: auto-generate PIN and send via SMS
            pin = generate_numeric_code(4)
            user.pin_hash = hash_password(pin)
            db.commit()
            await send_pin_sms(data.phone_number, pin)
            message = "OTP verified. Your PIN has been sent via SMS."
        else:
            db.commit()

        return {"message": message, "phone_number": data.phone_number, "company_id": company_id}
    finally:
        db.close()


# ──────────────────────────────────────────────
# FLOW 3: LOGIN WITH PIN
# ──────────────────────────────────────────────
@router.post("/login-pin", status_code=status.HTTP_200_OK)
async def login_pin(data: LoginPINRequest, response: Response):
    """Phone + PIN login. Issues access token + sets refresh token cookie.
    Only requires phone_number + pin — company is auto-discovered."""
    lookup = find_company_by_phone(data.phone_number)
    if not lookup:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    company_id = lookup["company_id"]
    db_gen = get_tenant_db(company_id)
    db: Session = next(db_gen)
    try:
        user = db.query(User).filter(User.phone_number == data.phone_number).first()
        if not user or not user.pin_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if not verify_password(data.pin, user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN"
            )
        if not user.phone_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Phone not verified"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
            )

        access_token = create_access_token(
            user.user_id,
            extra={"company_id": company_id, "role": "invitee"},
        )
        refresh_token = create_refresh_token(
            user.user_id,
            extra={"company_id": company_id},
        )

        # Store session record
        db.add(UserSession(
            user_id=user.user_id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        user.last_login = datetime.utcnow()
        db.commit()

        response.set_cookie(
            key="user_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "phone_number": user.phone_number,
                "full_name": user.full_name,
                "company_id": company_id,
            },
        }
    finally:
        db.close()


# ──────────────────────────────────────────────
# FLOW 4: RESET PIN
# ──────────────────────────────────────────────
@router.post("/reset-pin", status_code=status.HTTP_200_OK)
async def reset_pin(data: ResetPINRequest):
    """Reset PIN using OTP — revokes all user sessions.
    Only requires phone_number + otp + new_pin — company is auto-discovered."""
    lookup = find_company_by_phone(data.phone_number)
    if not lookup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found. Please contact your administrator.",
        )

    company_id = lookup["company_id"]
    db_gen = get_tenant_db(company_id)
    db: Session = next(db_gen)
    try:
        otp_record = (
            db.query(OTPCache)
            .filter(
                OTPCache.phone_number == data.phone_number,
                OTPCache.purpose == "VERIFICATION",
                OTPCache.is_used == False,
                OTPCache.expires_at > datetime.utcnow(),
            )
            .order_by(OTPCache.created_at.desc())
            .first()
        )
        if not otp_record or not verify_otp(data.otp, otp_record.otp_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
            )

        user = db.query(User).filter(User.phone_number == data.phone_number).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        otp_record.is_used = True
        user.pin_hash = hash_password(data.new_pin)

        # Revoke all sessions (logout all devices)
        db.query(UserSession).filter(UserSession.user_id == user.user_id).delete()
        db.commit()

        return {"message": "PIN reset successful. Please log in with your new PIN."}
    finally:
        db.close()


# ──────────────────────────────────────────────
# AUTH DEPENDENCY: get current user (handles both Workers and Admins)
# ──────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(user_bearer_scheme),
) -> dict:
    """
    Validates Bearer token.
    Works for both Plant Workers ("invitee") and Company Owners ("admin").

    Returns a dict with user_id, company_id, and role.
    """
    token = credentials.credentials

    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_token(token)
    role = payload.get("role")
    company_id = payload.get("company_id")

    # If role is missing (older tokens), try to infer it
    if not role:
        from app.database import get_db
        from app.models.admin import Admin
        db = next(get_db())
        try:
            admin = db.query(Admin).filter(Admin.id == user_id).first()
            if admin:
                role = "admin"
                company_id = admin.company_id
            else:
                role = "invitee"
        finally:
            db.close()

    return {"user_id": user_id, "company_id": company_id, "role": role}


@router.get("/me", status_code=status.HTTP_200_OK)
async def user_me(current: dict = Depends(get_current_user)):
    """Get current user identity from token claims (lightweight — no DB hit)."""
    return current


# ──────────────────────────────────────────────
# CONSOLIDATED PROFILE MANAGEMENT
# ──────────────────────────────────────────────
@router.get("/profile", status_code=status.HTTP_200_OK)
async def get_consolidated_profile(current: dict = Depends(get_current_user)):
    """
    Get the profile for the currently logged-in user.
    Automatically handles both 'admin' and 'user' (worker) roles.
    """
    from app.database import get_db
    from app.models.admin import Admin
    
    # If the user is an Admin, fetch from the public schema
    if current["role"] == "admin":
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            admin = db.query(Admin).filter(Admin.id == current["user_id"]).first()
            if not admin:
                raise HTTPException(status_code=404, detail="Admin not found")
            return {
                "user_id": admin.id,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "full_name": admin.full_name,
                "email": admin.email,
                "phone_country_code": admin.phone_country_code,
                "phone_number": admin.phone_number,
                "role": "admin"
            }
        finally:
            db.close()
            
    # Otherwise, fetch from the tenant schema
    else:
        db_gen = get_tenant_db(current["company_id"])
        db: Session = next(db_gen)
        try:
            user = db.query(User).filter(User.user_id == current["user_id"]).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "email": user.email,
                "phone_country_code": user.phone_country_code,
                "phone_number": user.phone_number,
                "role": "invitee"
            }
        finally:
            db.close()


@router.patch("/profile", status_code=status.HTTP_200_OK)
async def update_consolidated_profile(
    data: UserProfileUpdate, 
    current: dict = Depends(get_current_user)
):
    """
    Update the profile for the currently logged-in user.
    Automatically handles both 'admin' and 'user' (worker) roles.
    """
    from app.database import get_db
    from app.models.admin import Admin
    
    # If the user is an Admin, update the public schema
    if current["role"] == "admin":
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            admin = db.query(Admin).filter(Admin.id == current["user_id"]).first()
            if not admin:
                raise HTTPException(status_code=404, detail="Admin not found")
                
            if data.phone_number and data.phone_number != admin.phone_number:
                existing = db.query(Admin).filter(Admin.phone_number == data.phone_number).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Phone number is already in use")
            
            if data.first_name is not None: admin.first_name = data.first_name
            if data.last_name is not None: admin.last_name = data.last_name
            if data.phone_country_code is not None: admin.phone_country_code = data.phone_country_code
            if data.phone_number is not None: admin.phone_number = data.phone_number
            if data.email is not None: admin.email = data.email
                
            if admin.first_name or admin.last_name:
                admin.full_name = f"{admin.first_name or ''} {admin.last_name or ''}".strip()
                
            admin.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "message": "Admin profile updated successfully",
                "user": {
                    "user_id": admin.id,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "full_name": admin.full_name,
                    "email": admin.email,
                    "phone_country_code": admin.phone_country_code,
                    "phone_number": admin.phone_number,
                    "role": "admin"
                }
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    # Otherwise, update the tenant schema
    else:
        db_gen = get_tenant_db(current["company_id"])
        db: Session = next(db_gen)
        try:
            user = db.query(User).filter(User.user_id == current["user_id"]).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            if data.phone_number and data.phone_number != user.phone_number:
                existing = db.query(User).filter(User.phone_number == data.phone_number).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Phone number is already in use")
            
            if data.first_name is not None: user.first_name = data.first_name
            if data.last_name is not None: user.last_name = data.last_name
            if data.email is not None: user.email = data.email
            if data.phone_country_code is not None: user.phone_country_code = data.phone_country_code
            if data.phone_number is not None: user.phone_number = data.phone_number
                
            if user.first_name or user.last_name:
                user.full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

            db.commit()
            
            return {
                "message": "User profile updated successfully",
                "user": {
                    "user_id": user.user_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone_country_code": user.phone_country_code,
                    "phone_number": user.phone_number,
                    "role": "invitee"
                }
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
