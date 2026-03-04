"""Cryptography utilities using Argon2"""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Initialize Argon2 hasher with secure parameters
ph = PasswordHasher(
    time_cost=2,          # Number of iterations
    memory_cost=65536,    # 64 MB
    parallelism=1,        # Single thread
    hash_len=32,          # 32-byte hash
    salt_len=16           # 16-byte salt
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id
    
    Args:
        password: Plain text password
        
    Returns:
        Argon2 hash string ($argon2id$v=19$m=65536...)
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its Argon2 hash
    
    Args:
        password: Plain text password to verify
        password_hash: Argon2 hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def hash_otp(otp: str) -> str:
    """
    Hash an OTP using Argon2id
    
    Args:
        otp: Plain text OTP (6 digits)
        
    Returns:
        Argon2 hash string
    """
    return ph.hash(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    """
    Verify an OTP against its Argon2 hash
    
    Args:
        otp: Plain text OTP to verify
        otp_hash: Argon2 hash to verify against
        
    Returns:
        True if OTP matches, False otherwise
    """
    try:
        ph.verify(otp_hash, otp)
        return True
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    """
    Hash a refresh token using Argon2id
    
    Args:
        token: Plain text refresh token (JWT)
        
    Returns:
        Argon2 hash string
    """
    return ph.hash(token)


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its Argon2 hash
    
    Args:
        token: Plain text token to verify
        token_hash: Argon2 hash to verify against
        
    Returns:
        True if token matches, False otherwise
    """
    try:
        ph.verify(token_hash, token)
        return True
    except VerifyMismatchError:
        return False
