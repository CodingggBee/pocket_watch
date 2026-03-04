"""OTP generation utilities"""
import secrets
from app.config import get_settings

settings = get_settings()


def generate_otp() -> str:
    """
    Generate a cryptographically secure random 6-digit OTP
    
    Returns:
        6-digit OTP string (e.g., "127859")
    """
    # Generate random number between 0 and 999999
    otp_number = secrets.randbelow(1_000_000)
    
    # Pad with zeros to ensure 6 digits
    otp = str(otp_number).zfill(settings.OTP_LENGTH)
    
    return otp


def generate_numeric_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure random numeric code
    
    Args:
        length: Length of the code (default: 6)
        
    Returns:
        Numeric code string
    """
    max_value = 10 ** length
    code_number = secrets.randbelow(max_value)
    
    return str(code_number).zfill(length)
