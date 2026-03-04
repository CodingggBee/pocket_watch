"""Application configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


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
    GMAIL_USER: str = "ayeshashahidghgh@gmail.com"
    GMAIL_APP_PASSWORD: str = "jdujjeqlclwvovpj"

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

    # Stripe
    STRIPE_SECRET_KEY:str=""
    STRIPE_PUBLISHABLE_KEY:str=""
    STRIPE_WEBHOOK_SECRET:str=""

    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_critical_settings(self):
        """Validate critical settings are configured"""
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is required. "
                "Set it in Vercel dashboard: Settings → Environment Variables"
            )
        if self.ENVIRONMENT == "production" and self.JWT_SECRET == "temp-dev-secret-change-in-production":
            raise ValueError(
                "JWT_SECRET must be changed in production. "
                "Generate a secure random key and set it in environment variables."
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    # Only validate in production to allow graceful degradation in dev
    if settings.ENVIRONMENT == "production":
        try:
            settings.validate_critical_settings()
        except ValueError as e:
            print(f"⚠️  Configuration warning: {e}")
    return settings
