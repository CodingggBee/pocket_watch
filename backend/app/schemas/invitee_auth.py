"""Invitee authentication schemas"""
from pydantic import BaseModel, Field


# Send OTP
class SendOTPRequest(BaseModel):
    """Send OTP request schema"""
    phone_number: str = Field(..., min_length=10, max_length=20)


class SendOTPResponse(BaseModel):
    """Send OTP response schema"""
    message: str
    phone_number: str
    session_id: str


# Verify OTP
class VerifyOTPRequest(BaseModel):
    """Verify OTP and get PIN"""
    phone_number: str = Field(..., min_length=10, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    """Verify OTP response schema"""
    message: str
    phone_number: str
    pin_sent: bool


# Login with PIN
class LoginPINRequest(BaseModel):
    """Login with PIN request schema"""
    phone_number: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=4, max_length=4)


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: dict


# Reset PIN
class ResetPINRequest(BaseModel):
    """Reset PIN request schema"""
    phone_number: str = Field(..., min_length=10, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPINResponse(BaseModel):
    """Reset PIN response schema"""
    message: str
    phone_number: str
