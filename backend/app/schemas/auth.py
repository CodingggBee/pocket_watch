"""Pydantic schemas for admin authentication"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, field_validator
import re


class SignupRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ResendOTPRequest(BaseModel):
    email: EmailStr


class CreateAccountInfoRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    phone_country_code: Optional[str] = None
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain a special character")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


# ── Responses ──────────────────────────────────────────────


class SignupResponse(BaseModel):
    message: str
    email: str
    user_id: str
    company_id: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # access token lifetime in seconds
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class ForgotPasswordResponse(BaseModel):
    message: str
    email: str


class ResetPasswordResponse(BaseModel):
    message: str


class ResendOTPResponse(BaseModel):
    message: str
    email: str


class LogoutResponse(BaseModel):
    message: str


class CreateAccountInfoResponse(BaseModel):
    message: str
    user: Dict[str, Any]


class AdminProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_country_code: Optional[str] = None
    phone_number: Optional[str] = None
