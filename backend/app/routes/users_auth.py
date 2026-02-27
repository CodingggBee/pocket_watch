"""User (plant worker) authentication routes — multi-tenant schema"""

from datetime import datetime, timedelta
from typing import Optional, Generator

from app.config import get_settings
from app.database import get_tenant_db
from app.models.tenant.user import User
from app.models.tenant.otp_cache import OTPCache
from app.models.tenant.user_session import UserSession
from app.services.sms import send_sms_otp, send_pin_sms
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
)
from app.utils.otp import generate_numeric_code, generate_otp
from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

settings = get_settings()

router = APIRouter(prefix="/users/auth", tags=["User Authentication"])


# ──────────────────────────────────────────────
# Schemas (inline for conciseness)
# ──────────────────────────────────────────────
class SendOTPRequest(BaseModel):
    phone_number: str
    company_id: str   # required to select the right schema


class VerifyOTPRequest(BaseModel):
    phone_number: str
    company_id: str
    otp: str


class LoginPINRequest(BaseModel):
    phone_number: str
    company_id: str
    pin: str


class ResetPINRequest(BaseModel):
    phone_number: str
    company_id: str
    otp: str
    new_pin: str


# ──────────────────────────────────────────────
# Tenant DB dependency
# ──────────────────────────────────────────────
def _tenant_db(company_id: str) -> Generator[Session, None, None]:
    yield from get_tenant_db(company_id)


# ──────────────────────────────────────────────
# FLOW 1: SEND OTP
# ──────────────────────────────────────────────
@router.post("/send-otp", status_code=status.HTTP_200_OK)
async def send_otp(data: SendOTPRequest):
    """
    Send a 6-digit OTP to the user's phone number.
    Stores the hashed OTP in the tenant's otp_cache table.
    """
    db_gen = get_tenant_db(data.company_id)
    db: Session = next(db_gen)
    try:
        user = db.query(User).filter(User.phone_number == data.phone_number).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found. Please contact your administrator.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive."
            )

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

        await send_sms_otp(data.phone_number, otp_code)
        return {"message": "OTP sent successfully", "phone_number": data.phone_number}
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
    """
    db_gen = get_tenant_db(data.company_id)
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

        return {"message": message, "phone_number": data.phone_number}
    finally:
        db.close()


# ──────────────────────────────────────────────
# FLOW 3: LOGIN WITH PIN
# ──────────────────────────────────────────────
@router.post("/login-pin", status_code=status.HTTP_200_OK)
async def login_pin(data: LoginPINRequest, response: Response):
    """Phone + PIN login. Issues access token + sets refresh token cookie."""
    db_gen = get_tenant_db(data.company_id)
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
            extra={"company_id": data.company_id, "role": "user"},
        )
        refresh_token = create_refresh_token(
            user.user_id,
            extra={"company_id": data.company_id},
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
                "company_id": data.company_id,
            },
        }
    finally:
        db.close()


# ──────────────────────────────────────────────
# FLOW 4: RESET PIN
# ──────────────────────────────────────────────
@router.post("/reset-pin", status_code=status.HTTP_200_OK)
async def reset_pin(data: ResetPINRequest):
    """Reset PIN using OTP — revokes all user sessions."""
    db_gen = get_tenant_db(data.company_id)
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
# AUTH DEPENDENCY: get current user
# ──────────────────────────────────────────────
async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Validates Bearer token for a plant worker.

    Returns a dict with user_id, company_id, and role
    (does NOT hit the DB — the caller should query the tenant DB themselves).
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    company_id = get_company_id_from_token(token)
    return {"user_id": user_id, "company_id": company_id, "role": "user"}


@router.get("/me", status_code=status.HTTP_200_OK)
async def user_me(current: dict = Depends(get_current_user)):
    """Get current user identity from token claims (lightweight — no DB hit)."""
    return current
