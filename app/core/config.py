from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Agricultural Assistant Platform"
    APP_ENV: str = "development"
    SECRET_KEY: str
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./agritech.db"
    
    # Google Gemini API
    GEMINI_API_KEY: str
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
