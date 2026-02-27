"""SMS service using Twilio API"""
from twilio.rest import Client
from typing import Optional
from app.config import get_settings

settings = get_settings()

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


async def send_sms_otp(phone_number: str, otp: str) -> bool:
    """
    Send OTP via SMS using Twilio
    
    Args:
        phone_number: Recipient phone number (E.164 format: +1234567890)
        otp: 6-digit OTP code
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Create OTP message
        message_body = f"Your PocketWatch verification code is: {otp}\n\nThis code will expire in 10 minutes. Do not share this code with anyone."
        
        # Send SMS via Twilio
        message = twilio_client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        # Log success (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n[OK] SMS sent successfully!")
            print(f"[TO] To: {phone_number}")
            print(f"[OTP] OTP: {otp}")
            print(f"[SID] Message SID: {message.sid}\n")
        
        return True
        
    except Exception as e:
        # Log error (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n[ERR] Failed to send SMS to {phone_number}")
            print(f"Error: {str(e)}")
            print(f"[OTP] OTP (fallback): {otp}\n")
        
        return False


async def send_pin_sms(phone_number: str, pin: str) -> bool:
    """
    Send 4-digit PIN via SMS using Twilio
    
    Args:
        phone_number: Recipient phone number (E.164 format)
        pin: 4-digit PIN code
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Create PIN message
        message_body = f"Your PocketWatch login PIN is: {pin}\n\nUse this PIN to access your account. Keep it secure and do not share with anyone."
        
        # Send SMS via Twilio
        message = twilio_client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        # Log success (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n[OK] PIN SMS sent successfully!")
            print(f"[TO] To: {phone_number}")
            print(f"[PIN] PIN: {pin}")
            print(f"[SID] Message SID: {message.sid}\n")
        
        return True
        
    except Exception as e:
        # Log error (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n[ERR] Failed to send PIN SMS to {phone_number}")
            print(f"Error: {str(e)}")
            print(f"[PIN] PIN (fallback): {pin}\n")
        
        return False
