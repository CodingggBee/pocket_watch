"""Email service using Resend API"""
import resend
from typing import Optional
from app.config import get_settings

settings = get_settings()

# Configure Resend API
resend.api_key = settings.RESEND_API_KEY


def get_email_template(otp: str, purpose: str, user_name: Optional[str] = None) -> str:
    """
    Generate HTML email template for OTP
    
    Args:
        otp: 6-digit OTP code
        purpose: Email purpose (VERIFICATION or PASSWORD_RESET)
        user_name: Optional user name
        
    Returns:
        HTML email template string
    """
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    
    if purpose == "VERIFICATION":
        title = "Verify Your Email"
        message = "Thank you for signing up for PocketWatch! Please use the verification code below to complete your registration:"
        footer_text = "This code will expire in 10 minutes. If you didn't create an account, please ignore this email."
    else:  # PASSWORD_RESET
        title = "Reset Your Password"
        message = "We received a request to reset your password. Please use the code below to proceed:"
        footer_text = "This code will expire in 10 minutes. If you didn't request a password reset, please ignore this email."
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #ffffff;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a1a; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">
                                    🕐 PocketWatch
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #e5e5e5;">
                                    {greeting}
                                </p>
                                <p style="margin: 0 0 32px 0; font-size: 16px; line-height: 1.6; color: #e5e5e5;">
                                    {message}
                                </p>
                                
                                <!-- OTP Box -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 24px 0;">
                                            <div style="background-color: #262626; border: 2px solid #dc2626; border-radius: 12px; padding: 24px; display: inline-block;">
                                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #a3a3a3; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                                                    Verification Code
                                                </p>
                                                <p style="margin: 0; font-size: 42px; font-weight: 700; color: #dc2626; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                                    {otp}
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 32px 0 0 0; font-size: 14px; line-height: 1.6; color: #a3a3a3;">
                                    {footer_text}
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #0a0a0a; padding: 24px 32px; border-top: 1px solid #262626;">
                                <p style="margin: 0; font-size: 12px; color: #737373; text-align: center; line-height: 1.6;">
                                    © 2026 PocketWatch. All rights reserved.<br>
                                    This is an automated message, please do not reply.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html


async def send_otp_email(
    to_email: str,
    otp: str,
    purpose: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send OTP email using Resend
    
    Args:
        to_email: Recipient email address
        otp: 6-digit OTP code
        purpose: Email purpose (VERIFICATION or PASSWORD_RESET)
        user_name: Optional user name for personalization
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Generate email subject based on purpose
        if purpose == "VERIFICATION":
            subject = f"Verify Your PocketWatch Account - Code: {otp}"
        else:
            subject = f"Reset Your PocketWatch Password - Code: {otp}"
        
        # Get HTML template
        html_content = get_email_template(otp, purpose, user_name)
        
        # Send email via Resend
        params = {
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        
        # Log success (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n✅ Email sent successfully!")
            print(f"📧 To: {to_email}")
            print(f"🔐 OTP: {otp}")
            print(f"📨 Email ID: {email.get('id')}\n")
        
        return True
        
    except Exception as e:
        # Log error (for development)
        if settings.ENVIRONMENT == "development":
            print(f"\n❌ Failed to send email to {to_email}")
            print(f"Error: {str(e)}")
            print(f"🔐 OTP (fallback): {otp}\n")
        
        return False


async def send_verification_email(to_email: str, otp: str, user_name: Optional[str] = None) -> bool:
    """Send verification email"""
    return await send_otp_email(to_email, otp, "VERIFICATION", user_name)


async def send_password_reset_email(to_email: str, otp: str, user_name: Optional[str] = None) -> bool:
    """Send password reset email"""
    return await send_otp_email(to_email, otp, "PASSWORD_RESET", user_name)
