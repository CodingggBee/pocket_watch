"""Authentication routes"""

from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.models.admin import Admin
from app.models.admin_otp import AdminOTP, OTPPurpose
from app.models.admin_refresh_token import AdminRefreshToken
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutResponse,
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
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

settings = get_settings()
router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])


# ========================================
# FLOW 1: SIGNUP → EMAIL VERIFICATION
# ========================================


@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
async def signup(data: SignupRequest, db: Session = Depends(get_db)):
    """
    User Signup

    1. Validate email and password
    2. Check if email already exists
    3. Hash password with Argon2
    4. Create user in database (not verified)
    5. Generate 6-digit OTP
    6. Hash OTP with Argon2
    7. Store OTP in database
    8. Send OTP via email
    """
    # Check if email already exists
    existing_user = db.query(Admin).filter(Admin.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password
    password_hashed = hash_password(data.password)

    # Create admin user
    new_user = Admin(
        email=data.email,
        password_hash=password_hashed,
        is_verified=False,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate OTP
    otp_code = generate_otp()
    otp_hashed = hash_otp(otp_code)

    # Store OTP in database
    otp_record = AdminOTP(
        admin_id=new_user.id,
        otp_hash=otp_hashed,
        purpose=OTPPurpose.VERIFICATION,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )

    db.add(otp_record)
    db.commit()

    # Send OTP via email
    email_sent = await send_verification_email(to_email=new_user.email, otp=otp_code)

    if not email_sent:
        # Log warning but don't fail the request
        print(f"⚠️  Warning: Failed to send verification email to {new_user.email}")

    return SignupResponse(
        message="Signup successful! Please check your email for verification code.",
        email=new_user.email,
        user_id=new_user.id,
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(
    data: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)
):
    """
    Verify OTP and Complete Registration

    1. Find user by email
    2. Query latest unused OTP for VERIFICATION
    3. Verify OTP hash
    4. Mark OTP as used
    5. Set user as verified
    6. Generate access token (15 min)
    7. Generate refresh token (30 days)
    8. Hash and store refresh token
    9. Set HTTP-only cookie with refresh token
    10. Return access token and user data
    """
    # Find user
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find latest unused OTP
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

    # Verify OTP
    if not verify_otp(data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP"
        )

    # Mark OTP as used
    otp_record.used = True

    # Set user as verified
    user.is_verified = True

    db.commit()

    # Generate tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Hash and store refresh token
    refresh_token_hashed = hash_token(refresh_token)
    refresh_token_record = AdminRefreshToken(
        admin_id=user.id,
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
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 30 days in seconds
    )

    # Return response
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        },
    )


# ========================================
# FLOW 2: RETURNING USER LOGIN
# ========================================


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    User Login

    1. Find user by email
    2. Verify password with Argon2
    3. Check if user is verified
    4. Generate new access token (15 min)
    5. Generate new refresh token (30 days)
    6. Hash and store refresh token
    7. Set HTTP-only cookie
    8. Return access token and user data
    """
    # Find user
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Check if verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
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
    refresh_token_record = AdminRefreshToken(
        admin_id=user.id,
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
            "email": user.email,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        },
    )


# ========================================
# FLOW 3: PROTECTED ROUTE (Get Current User)
# ========================================


async def get_current_user(
    authorization: Optional[str] = None, db: Session = Depends(get_db)
) -> Admin:
    """
    Dependency to get current authenticated user

    1. Extract token from Authorization header
    2. Verify JWT signature and expiration
    3. Extract user_id from token
    4. Query database for user
    5. Return user object
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token (format: "Bearer <token>")
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
    user = db.query(Admin).filter(Admin.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Admin = Depends(get_current_user)):
    """
    Get Current User Profile

    Protected endpoint - requires valid access token
    """
    return current_user


# ========================================
# FLOW 4: TOKEN REFRESH
# ========================================


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token_endpoint(
    refresh_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)
):
    """
    Refresh Access Token

    1. Read refresh token from HTTP-only cookie
    2. Verify JWT signature and expiration
    3. Extract user_id from token
    4. Query database for all non-revoked refresh tokens
    5. Loop through and verify hash
    6. If match found, generate new access token
    7. Refresh token stays the same (reusable)
    8. Return new access token
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    # Verify refresh token JWT
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get all non-revoked refresh tokens for this user
    refresh_tokens = (
        db.query(AdminRefreshToken)
        .filter(
            AdminRefreshToken.admin_id == user_id,
            AdminRefreshToken.revoked == False,
            AdminRefreshToken.expires_at > datetime.utcnow(),
        )
        .all()
    )

    # Verify token hash against stored tokens
    token_found = False
    for token_record in refresh_tokens:
        if verify_token_hash(refresh_token, token_record.token_hash):
            token_found = True
            break

    if not token_found:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Generate new access token
    new_access_token = create_access_token(user_id)

    return RefreshTokenResponse(access_token=new_access_token, token_type="bearer")


# ========================================
# FLOW 5: PASSWORD RESET
# ========================================


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request Password Reset

    1. Find user by email
    2. Generate 6-digit OTP
    3. Hash OTP with Argon2
    4. Store OTP in database with PASSWORD_RESET purpose
    5. Send OTP via email
    """
    # Find user
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        # Don't reveal if email exists - return success anyway
        return ForgotPasswordResponse(
            message="If an account with this email exists, you will receive a password reset code.",
            email=data.email,
        )

    # Generate OTP
    otp_code = generate_otp()
    otp_hashed = hash_otp(otp_code)

    # Store OTP
    otp_record = AdminOTP(
        admin_id=user.id,
        otp_hash=otp_hashed,
        purpose=OTPPurpose.PASSWORD_RESET,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )

    db.add(otp_record)
    db.commit()

    # Send email
    email_sent = await send_password_reset_email(to_email=user.email, otp=otp_code)

    if not email_sent:
        print(f"⚠️  Warning: Failed to send password reset email to {user.email}")

    return ForgotPasswordResponse(
        message="If an account with this email exists, you will receive a password reset code.",
        email=data.email,
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset Password with OTP

    1. Find user by email
    2. Find latest unused OTP with PASSWORD_RESET purpose
    3. Verify OTP hash
    4. Mark OTP as used
    5. Hash new password with Argon2
    6. Update user password
    7. SECURITY: Revoke ALL refresh tokens (logout all devices)
    """
    # Find user
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find latest unused OTP
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

    # Update password
    user.password_hash = hash_password(data.new_password)

    # SECURITY: Revoke all refresh tokens (logout all devices)
    db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == user.id, AdminRefreshToken.revoked == False
    ).update({"revoked": True})

    db.commit()

    return ResetPasswordResponse(
        message="Password reset successful. Please login with your new password."
    )


# ========================================
# FLOW 6: RESEND OTP
# ========================================


@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(data: ResendOTPRequest, db: Session = Depends(get_db)):
    """
    Resend OTP

    1. Find user by email
    2. Generate new OTP
    3. Hash and store with appropriate purpose
    4. Send via email
    """
    # Find user
    user = db.query(Admin).filter(Admin.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Determine OTP purpose
    purpose = (
        OTPPurpose.VERIFICATION
        if data.purpose == "VERIFICATION"
        else OTPPurpose.PASSWORD_RESET
    )

    # Generate OTP
    otp_code = generate_otp()
    otp_hashed = hash_otp(otp_code)

    # Store OTP
    otp_record = AdminOTP(
        admin_id=user.id,
        otp_hash=otp_hashed,
        purpose=purpose,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )

    db.add(otp_record)
    db.commit()

    # Send email
    if purpose == OTPPurpose.VERIFICATION:
        email_sent = await send_verification_email(user.email, otp_code)
    else:
        email_sent = await send_password_reset_email(user.email, otp_code)

    if not email_sent:
        print(f"⚠️  Warning: Failed to resend OTP to {user.email}")

    return ResendOTPResponse(
        message=f"OTP has been resent to {user.email}", email=user.email
    )


# ========================================
# FLOW 7: LOGOUT
# ========================================


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    """
    Logout User

    1. Read refresh token from cookie
    2. Verify JWT and extract user_id
    3. Find matching token in database
    4. Set revoked = True
    5. Delete refresh token cookie
    """
    if not refresh_token:
        # No token to revoke, just clear cookie
        response.delete_cookie("refresh_token")
        return LogoutResponse(message="Logged out successfully")

    # Verify token
    user_id = verify_refresh_token(refresh_token)
    if user_id:
        # Find and revoke the specific token
        refresh_tokens = (
            db.query(AdminRefreshToken)
            .filter(
                AdminRefreshToken.admin_id == user_id,
                AdminRefreshToken.revoked == False,
            )
            .all()
        )

        for token_record in refresh_tokens:
            if verify_token_hash(refresh_token, token_record.token_hash):
                token_record.revoked = True
                db.commit()
                break

    # Delete cookie
    response.delete_cookie("refresh_token")

    return LogoutResponse(message="Logged out successfully")
