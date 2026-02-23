"""Database models"""

# New separate models
from app.models.admin import Admin
from app.models.admin_otp import AdminOTP
from app.models.admin_otp import OTPPurpose as AdminOTPPurpose
from app.models.admin_refresh_token import AdminRefreshToken
from app.models.invitee import Invitee
from app.models.invitee_otp import InviteeOTP
from app.models.invitee_otp import OTPPurpose as InviteeOTPPurpose
from app.models.invitee_refresh_token import InviteeRefreshToken
from app.models.otp import OTP, OTPPurpose
from app.models.refresh_token import RefreshToken

# Legacy models (kept for backward compatibility during migration)
from app.models.user import User, UserRole

__all__ = [
    "Admin",
    "Invitee",
    "AdminOTP",
    "InviteeOTP",
    "AdminOTPPurpose",
    "InviteeOTPPurpose",
    "AdminRefreshToken",
    "InviteeRefreshToken",
    "User",
    "UserRole",
    "OTP",
    "OTPPurpose",
    "RefreshToken",
]
