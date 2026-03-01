"""Application configuration"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str = ""

    # JWT
    JWT_SECRET: str = "temp-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ISSUER: str = "pocketwatch-api"
    JWT_AUDIENCE: str = "pocketwatch-app"

    # Email (Resend) - For Admin auth
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@example.com"

    # Email fallback (Gmail SMTP)
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""

    # SMS (Twilio) - For User auth
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Pinecone - For AI vector embeddings
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "pocketwatch-docs"

    # App
    APP_NAME: str = "Pocketwatch.ai"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"

    # OTP
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6

    # Environment
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
    return Settings()
