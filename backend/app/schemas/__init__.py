"""Pydantic schemas"""
from app.schemas.user import UserResponse
from app.schemas.auth import (
    SignupRequest, SignupResponse,
    LoginRequest, TokenResponse, RefreshTokenResponse,
    VerifyOTPRequest,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    ResendOTPRequest, ResendOTPResponse,
    LogoutResponse,
)

__all__ = [
    "UserResponse",
    "SignupRequest", "SignupResponse",
    "LoginRequest", "TokenResponse", "RefreshTokenResponse",
    "VerifyOTPRequest",
    "ForgotPasswordRequest", "ForgotPasswordResponse",
    "ResetPasswordRequest", "ResetPasswordResponse",
    "ResendOTPRequest", "ResendOTPResponse",
    "LogoutResponse",
]
