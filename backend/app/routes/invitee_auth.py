"""Invitee Authentication routes - Phone/PIN based"""

from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.models.invitee import Invitee
from app.models.invitee_otp import InviteeOTP, OTPPurpose
from app.models.invitee_refresh_token import InviteeRefreshToken
from app.schemas.invitee_auth import (
    LoginPINRequest,
    ResetPINRequest,
    ResetPINResponse,
    SendOTPRequest,
    SendOTPResponse,
    TokenResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.schemas.user import UserResponse
from app.services.sms import send_pin_sms, send_sms_otp
from app.utils.crypto import (
    hash_otp,
    hash_password,
    hash_token,
    verify_otp,
    verify_password,
    verify_token_hash,
)
from app.utils.jwt import create_access_token, create_refresh_token, verify_access_token
from app.utils.otp import generate_numeric_code, generate_otp
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

settings = get_settings()
router = APIRouter(prefix="/invitee/auth", tags=["Invitee Authentication"])


# ========================================
# FLOW 1: FIRST TIME LOGIN (OTP → PIN)
# ========================================


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(data: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to Invitee's Phone

    1. Find invitee by phone number
    2. Generate 6-digit OTP
    3. Hash OTP with Argon2
    4. Store OTP in database
    5. Send OTP via SMS
    """
    # Find user by phone
    user = db.query(Invitee).filter(Invitee.phone_number == data.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found. Please contact your administrator.",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    # Generate OTP
    otp_code = generate_otp()
    otp_hashed = hash_otp(otp_code)

    # Store OTP in database
    otp_record = InviteeOTP(
        invitee_id=user.id,
        otp_hash=otp_hashed,
        purpose=OTPPurpose.VERIFICATION,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )

    db.add(otp_record)
    db.commit()

    # Send OTP via SMS
    sms_sent = await send_sms_otp(phone_number=user.phone_number, otp=otp_code)

    if not sms_sent:
        print(f"⚠️  Warning: Failed to send OTP SMS to {user.phone_number}")

    return SendOTPResponse(
        message=f"OTP has been sent to {data.phone_number}",
        phone_number=data.phone_number,
        session_id=otp_record.id,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp_endpoint(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and Send PIN

    1. Find user by phone number
    2. Find latest unused OTP
    3. Verify OTP hash
    4. Mark OTP as used
    5. Set phone_verified = True
    6. Generate 4-digit PIN
    7. Hash and store PIN
    8. Send PIN via SMS
    9. Return success message
    """
    # Find user
    user = db.query(Invitee).filter(Invitee.phone_number == data.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find latest unused OTP
    otp_record = (
        db.query(InviteeOTP)
        .filter(
            InviteeOTP.invitee_id == user.id,
            InviteeOTP.purpose == OTPPurpose.VERIFICATION,
            InviteeOTP.used == False,
            InviteeOTP.expires_at > datetime.utcnow(),
        )
        .order_by(InviteeOTP.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    # Verify OTP
    if not verify_otp(data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP"
        )

    # Mark OTP as used
    otp_record.used = True

    # Set phone as verified
    user.phone_verified = True

    # Generate 4-digit PIN
    pin_code = generate_numeric_code(length=4)
    pin_hashed = hash_password(pin_code)  # Use same hashing as password

    # Store PIN
    user.pin_hash = pin_hashed

    db.commit()

    # Send PIN via SMS
    sms_sent = await send_pin_sms(phone_number=user.phone_number, pin=pin_code)

    if not sms_sent:
        print(f"⚠️  Warning: Failed to send PIN SMS to {user.phone_number}")

    return VerifyOTPResponse(
        message=f"Phone verified! Your 4-digit PIN has been sent to {data.phone_number}",
        phone_number=data.phone_number,
        pin_sent=True,
    )


# ========================================
# FLOW 2: SUBSEQUENT LOGIN (PIN ONLY)
# ========================================


@router.post("/login-pin", response_model=TokenResponse)
async def login_with_pin(
    data: LoginPINRequest, response: Response, db: Session = Depends(get_db)
):
    """
    Login with 4-Digit PIN

    1. Find user by phone number
    2. Verify PIN with Argon2
    3. Check if phone verified
    4. Generate access token (15 min)
    5. Generate refresh token (30 days)
    6. Hash and store refresh token
    7. Set HTTP-only cookie
    8. Return access token and user data
    """
    # Find user
    user = db.query(Invitee).filter(Invitee.phone_number == data.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or PIN",
        )

    # Check if PIN is set
    if not user.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN not set. Please complete OTP verification first.",
        )

    # Verify PIN
    if not verify_password(data.pin, user.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or PIN",
        )

    # Check if phone verified
    if not user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone not verified. Please verify your phone first.",
        )

    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    # Generate tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Hash and store refresh token
    refresh_token_hashed = hash_token(refresh_token)
    refresh_token_record = InviteeRefreshToken(
        invitee_id=user.id,
        token_hash=refresh_token_hashed,
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )

    db.add(refresh_token_record)
    db.commit()

    # Set HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "role": "invitee",
            "phone_verified": user.phone_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        },
    )


# ========================================
# FLOW 3: RESET PIN
# ========================================


@router.post("/reset-pin", response_model=ResetPINResponse)
async def reset_pin(data: ResetPINRequest, db: Session = Depends(get_db)):
    """
    Reset PIN

    1. Find user by phone number
    2. Find latest unused OTP with PASSWORD_RESET purpose
    3. Verify OTP hash
    4. Mark OTP as used
    5. Generate new 4-digit PIN
    6. Hash and update PIN
    7. Send new PIN via SMS
    8. SECURITY: Revoke ALL refresh tokens (logout all devices)
    """
    # Find user
    user = db.query(Invitee).filter(Invitee.phone_number == data.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find latest unused OTP
    otp_record = (
        db.query(InviteeOTP)
        .filter(
            InviteeOTP.invitee_id == user.id,
            InviteeOTP.purpose == OTPPurpose.PIN_RESET,
            InviteeOTP.used == False,
            InviteeOTP.expires_at > datetime.utcnow(),
        )
        .order_by(InviteeOTP.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    # Verify OTP
    if not verify_otp(data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP"
        )

    # Mark OTP as used
    otp_record.used = True

    # Generate new PIN
    new_pin = generate_numeric_code(length=4)
    new_pin_hashed = hash_password(new_pin)

    # Update PIN
    user.pin_hash = new_pin_hashed

    # SECURITY: Revoke all refresh tokens (logout all devices)
    db.query(InviteeRefreshToken).filter(
        InviteeRefreshToken.invitee_id == user.id, InviteeRefreshToken.revoked == False
    ).update({"revoked": True})

    db.commit()

    # Send new PIN via SMS
    sms_sent = await send_pin_sms(phone_number=user.phone_number, pin=new_pin)

    if not sms_sent:
        print(f"⚠️  Warning: Failed to send new PIN SMS to {user.phone_number}")

    return ResetPINResponse(
        message="PIN reset successful. Your new PIN has been sent via SMS.",
        phone_number=data.phone_number,
    )


# ========================================
# PROTECTED ROUTE (Get Current User)
# ========================================


async def get_current_invitee(
    authorization: Optional[str] = None, db: Session = Depends(get_db)
) -> Invitee:
    """
    Dependency to get current authenticated invitee
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token and get user_id
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(Invitee).filter(Invitee.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not an invitee",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Invitee = Depends(get_current_invitee)):
    """
    Get Current Invitee Profile

    Protected endpoint - requires valid access token
    """
    return current_user
