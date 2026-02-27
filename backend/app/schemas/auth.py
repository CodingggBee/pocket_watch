"""Pydantic schemas for admin authentication"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, field_validator
import re


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain a digit")
        return v


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


# ── Responses ──────────────────────────────────────────────


class SignupResponse(BaseModel):
    message: str
    email: str
    user_id: str
    company_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


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
