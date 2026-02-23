"""Authentication schemas"""
from pydantic import BaseModel, EmailStr, Field


# Signup
class SignupRequest(BaseModel):
    """Signup request schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class SignupResponse(BaseModel):
    """Signup response schema"""
    message: str
    email: EmailStr
    user_id: str


# Verify OTP
class VerifyOTPRequest(BaseModel):
    """Verify OTP request schema"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: dict


# Login
class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


# Refresh Token
class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""
    access_token: str
    token_type: str = "bearer"


# Forgot Password
class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response schema"""
    message: str
    email: EmailStr


# Reset Password
class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)


class ResetPasswordResponse(BaseModel):
    """Reset password response schema"""
    message: str


# Resend OTP
class ResendOTPRequest(BaseModel):
    """Resend OTP request schema"""
    email: EmailStr
    purpose: str = Field(..., pattern="^(VERIFICATION|PASSWORD_RESET)$")


class ResendOTPResponse(BaseModel):
    """Resend OTP response schema"""
    message: str
    email: EmailStr


# Logout
class LogoutResponse(BaseModel):
    """Logout response schema"""
    message: str
