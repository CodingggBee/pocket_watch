"""JWT token utilities"""
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()


def create_access_token(user_id: str, extra: Optional[Dict] = None) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User UUID
        extra: Optional extra claims (e.g. {"company_id": "...", "role": "admin"})

    Returns:
        Encoded JWT access token (valid for ACCESS_TOKEN_EXPIRE_MINUTES)
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, extra: Optional[Dict] = None) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User UUID
        extra: Optional extra claims

    Returns:
        Encoded JWT refresh token (valid for REFRESH_TOKEN_EXPIRE_DAYS)
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and verify a JWT token. Returns payload or None on failure."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_access_token(token: str) -> Optional[str]:
    """Verify access token. Returns user_id (sub) or None."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


def verify_refresh_token(token: str) -> Optional[str]:
    """Verify refresh token. Returns user_id (sub) or None."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload.get("sub")


def get_company_id_from_token(token: str) -> Optional[str]:
    """Extract company_id claim from a token (access or refresh)."""
    payload = decode_token(token)
    return payload.get("company_id") if payload else None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiration datetime of a token."""
    payload = decode_token(token)
    if not payload:
        return None
    exp = payload.get("exp")
    return datetime.fromtimestamp(exp) if exp else None
