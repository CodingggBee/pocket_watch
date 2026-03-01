"""
Email service — Resend primary, Gmail SMTP fallback.
Theme: PocketWatch.AI dark design (black bg, red accents).
"""

import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import resend
from app.config import get_settings

settings = get_settings()


# Lazily configure Resend so a missing key doesn't crash at import time
def _init_resend() -> None:
    if settings.RESEND_API_KEY and not settings.RESEND_API_KEY.startswith("re_your"):
        resend.api_key = settings.RESEND_API_KEY


# ──────────────────────────────────────────────────────────────────────────────
# HTML TEMPLATE
# ──────────────────────────────────────────────────────────────────────────────


def get_email_template(otp: str, purpose: str, user_name: Optional[str] = None) -> str:
    """Return a dark-themed HTML email for OTP delivery."""

    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    expire_min = settings.OTP_EXPIRE_MINUTES

    if purpose == "VERIFICATION":
        title = "Verify Your Email"
        badge_label = "Email Verification"
        message = (
            "Welcome to <strong>PocketWatch.AI</strong> — your smart SPC & AI coaching "
            "platform for manufacturing. Use the code below to verify your email address "
            "and activate your account."
        )
        footer_note = (
            f"This code expires in <strong>{expire_min} minutes</strong>. "
            "If you didn't create a PocketWatch.AI account, you can safely ignore this email."
        )
        icon = "✉"
    else:  # PASSWORD_RESET
        title = "Reset Your Password"
        badge_label = "Password Reset"
        message = (
            "We received a request to reset the password for your <strong>PocketWatch.AI</strong> "
            "account. Use the code below to set a new password."
        )
        footer_note = (
            f"This code expires in <strong>{expire_min} minutes</strong>. "
            "If you didn't request a password reset, no action is needed — your account is safe."
        )
        icon = "🔒"

    # Build individual digit cells for the OTP
    otp_cells = ""
    for digit in otp:
        otp_cells += (
            f'<td style="padding: 0 4px;">'
            f'<div style="'
            f"  width: 48px; height: 58px;"
            f"  background: #1e1e1e;"
            f"  border: 2px solid #dc2626;"
            f"  border-radius: 10px;"
            f"  display: inline-block;"
            f"  font-size: 30px;"
            f"  font-weight: 700;"
            f"  color: #ffffff;"
            f"  font-family: 'Courier New', monospace;"
            f"  line-height: 58px;"
            f"  text-align: center;"
            f"  vertical-align: middle;"
            f'">{digit}</div>'
            f"</td>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — PocketWatch.AI</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a;padding:40px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="580" cellpadding="0" cellspacing="0"
               style="max-width:580px;background-color:#111111;border-radius:20px;overflow:hidden;border:1px solid #2a2a2a;">

          <!-- ── HEADER ── -->
          <tr>
            <td style="background:linear-gradient(135deg,#b91c1c 0%,#dc2626 50%,#991b1b 100%);padding:36px 40px 28px 40px;text-align:center;">
              <!-- Brand -->
              <div style="margin-bottom:12px;">
                <span style="font-size:28px;font-weight:900;color:#ffffff;letter-spacing:3px;text-transform:uppercase;">
                  POCKET<span style="color:#fff;border-bottom:3px solid rgba(255,255,255,0.6);">W</span>ATCH
                </span>
                <span style="font-size:16px;font-weight:400;color:rgba(255,255,255,0.75);letter-spacing:1px;">.AI</span>
              </div>
              <div style="display:inline-block;background:rgba(0,0,0,0.25);border-radius:20px;padding:5px 16px;margin-top:4px;">
                <span style="font-size:12px;color:rgba(255,255,255,0.85);letter-spacing:1.5px;text-transform:uppercase;font-weight:600;">
                  {badge_label}
                </span>
              </div>
            </td>
          </tr>

          <!-- ── GREETING ── -->
          <tr>
            <td style="padding:36px 40px 0 40px;">
              <p style="margin:0 0 8px 0;font-size:22px;font-weight:700;color:#f5f5f5;">
                {icon}&nbsp; {title}
              </p>
              <p style="margin:0;font-size:15px;color:#a3a3a3;">
                {greeting}
              </p>
            </td>
          </tr>

          <!-- ── MESSAGE ── -->
          <tr>
            <td style="padding:16px 40px 28px 40px;">
              <p style="margin:0;font-size:15px;line-height:1.8;color:#c5c5c5;">
                {message}
              </p>
            </td>
          </tr>

          <!-- ── OTP BOX ── -->
          <tr>
            <td style="padding:0 40px 32px 40px;">
              <div style="background:#0d0d0d;border:1px solid #2a2a2a;border-radius:14px;padding:28px 20px;text-align:center;">
                <p style="margin:0 0 18px 0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#737373;font-weight:600;">
                  Your One-Time Code
                </p>
                <!-- OTP digit table -->
                <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
                  <tr>{otp_cells}</tr>
                </table>
                <p style="margin:18px 0 0 0;font-size:12px;color:#525252;">
                  Expires in {expire_min} minutes &nbsp;·&nbsp; Do not share this code
                </p>
              </div>
            </td>
          </tr>

          <!-- ── NOTICE ── -->
          <tr>
            <td style="padding:0 40px 36px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#1a1212;border-left:3px solid #dc2626;border-radius:0 8px 8px 0;">
                <tr>
                  <td style="padding:14px 18px;">
                    <p style="margin:0;font-size:13px;line-height:1.6;color:#9a9a9a;">
                      {footer_note}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── DIVIDER ── -->
          <tr>
            <td style="padding:0 40px;">
              <div style="height:1px;background:linear-gradient(to right,transparent,#2a2a2a,transparent);"></div>
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="padding:24px 40px 32px 40px;text-align:center;">
              <p style="margin:0 0 6px 0;font-size:14px;font-weight:700;color:#dc2626;letter-spacing:1px;">
                POCKETWATCH.AI
              </p>
              <p style="margin:0;font-size:12px;color:#525252;line-height:1.7;">
                Smart SPC &amp; AI Coaching Platform for Manufacturing<br>
                &copy; 2026 PocketWatch.AI &mdash; All rights reserved.<br>
                This is an automated message &mdash; please do not reply.
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>

</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# GMAIL SMTP FALLBACK
# ──────────────────────────────────────────────────────────────────────────────


def _send_via_gmail(to_email: str, subject: str, html_content: str) -> bool:
    """Send email through Gmail SMTP using an App Password. Returns True on success."""
    gmail_user = settings.GMAIL_USER
    gmail_pass = settings.GMAIL_APP_PASSWORD

    if not gmail_user or not gmail_pass:
        print(
            "[GMAIL] GMAIL_USER or GMAIL_APP_PASSWORD not configured — skipping fallback."
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"PocketWatch.AI <{gmail_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, to_email, msg.as_string())

        print(f"[GMAIL ✓] Fallback email sent to {to_email}")
        return True

    except Exception as exc:
        print(f"[GMAIL ✗] Fallback failed for {to_email}: {exc}")
        if settings.ENVIRONMENT == "development":
            traceback.print_exc()
        return False


# ──────────────────────────────────────────────────────────────────────────────
# PRIMARY SEND FUNCTION
# ──────────────────────────────────────────────────────────────────────────────


async def send_otp_email(
    to_email: str,
    otp: str,
    purpose: str,
    user_name: Optional[str] = None,
) -> bool:
    """
    Send an OTP email.

    Strategy:
      1. Try Resend (primary).
      2. On any error, fall back to Gmail SMTP.
      3. Return True if at least one channel succeeds.
    """
    if purpose == "VERIFICATION":
        subject = f"PocketWatch.AI — Verify your email ({otp})"
    else:
        subject = f"PocketWatch.AI — Reset your password ({otp})"

    html_content = get_email_template(otp, purpose, user_name)

    # ── 1. Try Resend ────────────────────────────────────────────────
    resend_ok = False
    try:
        _init_resend()
        if settings.RESEND_API_KEY and not settings.RESEND_API_KEY.startswith(
            "re_your"
        ):
            print(f"[RESEND] Attempting to send to {to_email}...")
            result = resend.Emails.send(
                {
                    "from": settings.FROM_EMAIL,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                }
            )
            email_id = (
                result.get("id")
                if isinstance(result, dict)
                else getattr(result, "id", None)
            )
            resend_ok = True
            print(f"[RESEND ✓] Email sent to {to_email} | id={email_id}")
        else:
            print(f"[RESEND] API key not configured — skipping Resend for {to_email}.")
    except Exception as exc:
        print(f"[RESEND ✗] Failed for {to_email}: {exc}")
        print(f"[EMAIL]  → Falling back to Gmail App Password for {to_email}...")
        if settings.ENVIRONMENT == "development":
            traceback.print_exc()

    if resend_ok:
        return True

    # ── 2. Gmail SMTP fallback ───────────────────────────────────────
    print(f"[GMAIL] Attempting fallback send to {to_email}...")
    gmail_ok = _send_via_gmail(to_email, subject, html_content)

    if not gmail_ok and settings.ENVIRONMENT == "development":
        # Last resort: print OTP to console so dev can proceed
        print(f"\n{'='*50}")
        print(f"  [DEV FALLBACK] Could not send email to {to_email}")
        print(f"  OTP: {otp}")
        print(f"{'='*50}\n")

    return gmail_ok


# ──────────────────────────────────────────────────────────────────────────────
# CONVENIENCE WRAPPERS
# ──────────────────────────────────────────────────────────────────────────────


async def send_verification_email(
    to_email: str, otp: str, user_name: Optional[str] = None
) -> bool:
    """Send email-verification OTP."""
    return await send_otp_email(to_email, otp, "VERIFICATION", user_name)


async def send_password_reset_email(
    to_email: str, otp: str, user_name: Optional[str] = None
) -> bool:
    """Send password-reset OTP."""
    return await send_otp_email(to_email, otp, "PASSWORD_RESET", user_name)
