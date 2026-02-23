"""JWT token utilities"""
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()


def create_access_token(user_id: str) -> str:
    """
    Create a JWT access token
    
    Args:
        user_id: User UUID
        
    Returns:
        Encoded JWT access token (valid for 15 minutes)
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,           # Subject (user ID)
        "type": "access",          # Token type
        "iat": now,                # Issued at
        "exp": expires_at,         # Expiration
        "iss": settings.JWT_ISSUER,      # Issuer
        "aud": settings.JWT_AUDIENCE     # Audience
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token
    
    Args:
        user_id: User UUID
        
    Returns:
        Encoded JWT refresh token (valid for 30 days)
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user_id,           # Subject (user ID)
        "type": "refresh",         # Token type
        "iat": now,                # Issued at
        "exp": expires_at,         # Expiration
        "iss": settings.JWT_ISSUER,      # Issuer
        "aud": settings.JWT_AUDIENCE     # Audience
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token


def decode_token(token: str) -> Optional[Dict]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Invalid token
        return None


def verify_access_token(token: str) -> Optional[str]:
    """
    Verify an access token and extract user ID
    
    Args:
        token: JWT access token
        
    Returns:
        User ID if valid, None otherwise
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    # Check token type
    if payload.get("type") != "access":
        return None
    
    return payload.get("sub")


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and extract user ID
    
    Args:
        token: JWT refresh token
        
    Returns:
        User ID if valid, None otherwise
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    # Check token type
    if payload.get("type") != "refresh":
        return None
    
    return payload.get("sub")


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration datetime of a token
    
    Args:
        token: JWT token
        
    Returns:
        Expiration datetime if valid, None otherwise
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    exp_timestamp = payload.get("exp")
    if not exp_timestamp:
        return None
    
    return datetime.fromtimestamp(exp_timestamp)
