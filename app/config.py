"""
Configuration management using Pydantic Settings.
All environment variables are loaded and validated here.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "AI Receptionist"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # AI Services
    GROQ_API_KEY: str
    DEEPSEEK_API_KEY: Optional[str] = None
    CARTESIA_API_KEY: str
    
    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str
    
    # Google Calendar
    GOOGLE_CREDENTIALS_PATH: str = "google_credentials.json"
    GOOGLE_CALENDAR_ID: str = "primary"
    
    # Business Configuration
    BUSINESS_NAME: str = "Hercules Detailing"
    BUSINESS_TIMEZONE: str = "America/Chicago"
    APPOINTMENT_DURATION_MINUTES: int = 60
    BUSINESS_HOURS_START: str = "09:00"
    BUSINESS_HOURS_END: str = "18:00"
    
    # Voice Agent Configuration
    AGENT_NAME: str = "Kylie"
    AGENT_VOICE: str = "female-1"
    AGENT_SPEED: float = 1.1
    STT_MODEL: str = "whisper-large-v3"
    LLM_MODEL: str = "deepseek-chat"
    TTS_MODEL: str = "sonic-english"
    
    # Security
    API_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CALL_DURATION_MINUTES: int = 15
    
    @validator("ALLOWED_ORIGINS")
    def parse_origins(cls, v):
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in v.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()