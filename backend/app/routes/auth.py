"""Authentication routes — Admin (company owner)"""

from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.models.admin import Admin
from app.models.admin_otp import AdminOTP, OTPPurpose
from app.models.admin_refresh_token import AdminRefreshToken
from app.models.company import Company
from app.schemas.auth import (
    CreateAccountInfoRequest,
    CreateAccountInfoResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyOTPRequest,
)
from app.schemas.user import UserResponse
from app.services.email import send_password_reset_email, send_verification_email
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
    get_token_expiry,
    verify_access_token,
    verify_refresh_token,
)
from app.utils.otp import generate_otp
from app.utils.schema import provision_tenant_tables
from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

settings = get_settings()
router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])

# Security scheme — shows the lock/Authorize button in Swagger UI
bearer_scheme = HTTPBearer()


# ========================================
# FLOW 1: SIGNUP → EMAIL VERIFICATION
# Creates Company + provisions tenant schema
# ========================================


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest,
    response: Response,
    db: Session = Depends(get_db)
):

    existing_admin = db.query(Admin).filter(Admin.email == data.email).first()

    # =========================
    # USER ALREADY EXISTS
    # =========================
    if existing_admin:

        #  VERIFIED + PROFILE COMPLETED → LOGIN
        if existing_admin.is_verified and existing_admin.profile_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please login."
            )

        # =========================
        # NEED OTP (UNVERIFIED OR PROFILE NOT COMPLETED)
        # =========================

        # invalidate old unused OTPs
        db.query(AdminOTP).filter(
            AdminOTP.admin_id == existing_admin.id,
            AdminOTP.purpose == OTPPurpose.VERIFICATION,
            AdminOTP.used == False,
        ).update({"used": True})

        otp_code = generate_otp()

        otp_record = AdminOTP(
            admin_id=existing_admin.id,
            otp_hash=hash_otp(otp_code),
            purpose=OTPPurpose.VERIFICATION,
            used=False,
            expires_at=datetime.utcnow() + timedelta(
                minutes=settings.OTP_EXPIRE_MINUTES
            ),
        )

        db.add(otp_record)
        db.commit()

        await send_verification_email(
            to_email=existing_admin.email,
            otp=otp_code
        )

        db.commit()

        return SignupResponse(
            message="Verification required. Please verify OTP sent to your email.",
            email=existing_admin.email,
            user_id=existing_admin.id,
            company_id=existing_admin.company_id,
        )

    # =========================
    # NEW USER — CREATE ACCOUNT
    # =========================
    else:
        new_company = Company(
            company_name=None,
            is_active=True,
        )
        db.add(new_company)
        db.flush()  # get company_id without full commit

        new_admin = Admin(
            email=data.email,
            company_id=new_company.company_id,
            is_verified=False,
            is_active=True,
            profile_completed=False,
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        db.refresh(new_company)

        otp_code = generate_otp()
        db.add(AdminOTP(
            admin_id=new_admin.id,
            otp_hash=hash_otp(otp_code),
            purpose=OTPPurpose.VERIFICATION,
            used=False,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        ))
        db.commit()

        await send_verification_email(to_email=new_admin.email, otp=otp_code)

        return SignupResponse(
            message="Signup successful! Please check your email for the verification code.",
            email=new_admin.email,
            user_id=new_admin.id,
            company_id=new_company.company_id,
        )


# ========================================
# FLOW 2: VERIFY OTP
# ========================================


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(
    data: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)
):
    """Verify email OTP, provision tenant schema, mark admin as verified, issue tokens."""
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_record = (
        db.query(AdminOTP)
        .filter(
            AdminOTP.admin_id == user.id,
            AdminOTP.purpose == OTPPurpose.VERIFICATION,
            AdminOTP.used == False,
            AdminOTP.expires_at > datetime.utcnow(),
        )
        .order_by(AdminOTP.created_at.desc())
        .first()
    )
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )
    if not verify_otp(data.otp, otp_record.otp_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    otp_record.used = True
    user.is_verified = True
    db.commit()

    # Provision the tenant schema now that the email is verified
    # Only create if not already provisioned (idempotent)
    try:
        provision_tenant_tables(user.company_id)
    except Exception as e:
        print(f"Warning: Failed to provision tenant schema: {e}")

    company_id = user.company_id
    user_id = user.id

    access_token = create_access_token(user_id, extra={"company_id": company_id})
    refresh_token = create_refresh_token(user_id)

    db.add(AdminRefreshToken(
        admin_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    ))
    db.commit()

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
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "company_id": company_id,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "profile_completed": user.profile_completed,
            "created_at": user.created_at.isoformat(),
        },
    )


# ========================================
# AUTH DEPENDENCY: get current admin
# ========================================


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    """Validates Bearer token and returns the Admin object."""
    token = credentials.credentials

    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(Admin).filter(Admin.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    return user


# ========================================
# FLOW 3: CREATE ACCOUNT INFO (requires auth)
# ========================================


@router.post("/create-account-info", response_model=CreateAccountInfoResponse)
async def create_account_info(
    data: CreateAccountInfoRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Complete the admin profile after OTP verification.
    Sets first name, last name, phone, password.
    Requires Bearer token (obtained from verify-otp).
    """
    admin = db.query(Admin).filter(Admin.id == current_admin.id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    if admin.profile_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account info already completed. Use the update profile endpoint instead.",
        )

    admin.first_name = data.first_name
    admin.last_name = data.last_name
    admin.full_name = f"{data.first_name} {data.last_name}"
    admin.phone_number = data.phone_number
    admin.phone_country_code = data.phone_country_code
    admin.password_hash = hash_password(data.password)
    admin.profile_completed = True
    admin.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(admin)

    return CreateAccountInfoResponse(
        message="Account info saved successfully.",
        user={
            "id": admin.id,
            "email": admin.email,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "full_name": admin.full_name,
            "phone_number": admin.phone_number,
            "company_id": admin.company_id,
            "profile_completed": admin.profile_completed,
        },
    )


# ========================================
# FLOW 4: LOGIN
# ========================================


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Email + password login for admin / company owner."""
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )
    if not user.profile_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete your account setup first.",
        )

    access_token = create_access_token(user.id, extra={"company_id": user.company_id})
    refresh_token = create_refresh_token(user.id)

    db.add(AdminRefreshToken(
        admin_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    ))
    db.commit()

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
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "company_id": user.company_id,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "profile_completed": user.profile_completed,
            "created_at": user.created_at.isoformat(),
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Admin = Depends(get_current_admin)):
    """Get current admin profile."""
    return current_user


# ========================================
# FLOW 5: TOKEN REFRESH
# ========================================


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token_endpoint(
    data: Optional[RefreshTokenRequest] = None,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    """
    Issue a new access token using a refresh token.

    Accepts refresh token from:
      - Request body: {"refresh_token": "..."} (for mobile apps)
      - HTTP-only cookie (for web browsers)
    """
    # Prefer body token (mobile), fall back to cookie (web)
    token = (data.refresh_token if data else None) or refresh_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    user_id = verify_refresh_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    tokens = (
        db.query(AdminRefreshToken)
        .filter(
            AdminRefreshToken.admin_id == user_id,
            AdminRefreshToken.revoked == False,
            AdminRefreshToken.expires_at > datetime.utcnow(),
        )
        .all()
    )

    if not any(verify_token_hash(token, t.token_hash) for t in tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get company_id for the new token
    admin = db.query(Admin).filter(Admin.id == user_id).first()
    company_id = admin.company_id if admin else None
    new_access_token = create_access_token(user_id, extra={"company_id": company_id})
    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ========================================
# FLOW 5: FORGOT / RESET PASSWORD
# ========================================


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password-reset OTP (always returns success to prevent enumeration)."""
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if user:
        otp_code = generate_otp()
        db.add(AdminOTP(
            admin_id=user.id,
            otp_hash=hash_otp(otp_code),
            purpose=OTPPurpose.PASSWORD_RESET,
            used=False,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        ))
        db.commit()
        await send_password_reset_email(to_email=user.email, otp=otp_code, user_name=user.full_name)

    return ForgotPasswordResponse(
        message="If an account with this email exists, you will receive a password reset code.",
        email=data.email,
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using OTP — revokes all existing refresh tokens."""
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_record = (
        db.query(AdminOTP)
        .filter(
            AdminOTP.admin_id == user.id,
            AdminOTP.purpose == OTPPurpose.PASSWORD_RESET,
            AdminOTP.used == False,
            AdminOTP.expires_at > datetime.utcnow(),
        )
        .order_by(AdminOTP.created_at.desc())
        .first()
    )
    if not otp_record or not verify_otp(data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    otp_record.used = True
    user.password_hash = hash_password(data.new_password)
    db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == user.id, AdminRefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()

    return ResetPasswordResponse(message="Password reset successful. Please login.")


# ========================================
# FLOW 6: RESEND OTP
# ========================================


@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(data: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend verification OTP to the admin's email."""
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified.",
        )

    # Invalidate old unused OTPs
    db.query(AdminOTP).filter(
        AdminOTP.admin_id == user.id,
        AdminOTP.purpose == OTPPurpose.VERIFICATION,
        AdminOTP.used == False,
    ).update({"used": True})

    otp_code = generate_otp()
    db.add(AdminOTP(
        admin_id=user.id,
        otp_hash=hash_otp(otp_code),
        purpose=OTPPurpose.VERIFICATION,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    ))
    db.commit()

    email_sent = await send_verification_email(user.email, otp_code, user_name=user.full_name)
    if not email_sent:
        print(f"Warning: Failed to send verification email to {user.email}")

    return ResendOTPResponse(message=f"OTP has been resent to {user.email}", email=user.email)


# ========================================
# FLOW 7: LOGOUT
# ========================================


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    data: Optional[RefreshTokenRequest] = None,   # for mobile
    refresh_token: Optional[str] = Cookie(None),  # for web
    db: Session = Depends(get_db),
):
    """
    Logout user by revoking the current refresh token.

    Accepts refresh token from:
    - request body (mobile apps)
    - HTTP-only cookie (web apps)
    """
    # Prefer body token → fallback to cookie
    token = (data.refresh_token if data else None) or refresh_token

    if not token:
        # No token → still return success (user already logged out)
        response.delete_cookie("refresh_token")
        return LogoutResponse(message="Logged out successfully")

    # Verify JWT structure & extract user_id
    user_id = verify_refresh_token(token)

    if user_id:
        # Get all active tokens of that user
        tokens = (
            db.query(AdminRefreshToken)
            .filter(
                AdminRefreshToken.admin_id == user_id,
                AdminRefreshToken.revoked == False,
            )
            .all()
        )

        # Revoke ONLY the matching token
        for t in tokens:
            if verify_token_hash(token, t.token_hash):
                t.revoked = True
                db.commit()
                break

    # Remove cookie from browser
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    return LogoutResponse(message="Logged out successfully")
