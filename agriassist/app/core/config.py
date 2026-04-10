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
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"
    
    # Twilio API
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_API_KEY: Optional[str] = None
    TWILIO_API_SECRET: Optional[str] = None
    TWILIO_TWIML_APP_SID: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # ===============================
    # POLYGON AMOY NETWORK
    # ===============================
    POLYGON_AMOY_RPC_URL: str
    POLYGON_AMOY_CHAIN_ID: int

    # ===============================
    # SYSTEM (ADMIN) WALLET
    # ===============================
    SYSTEM_WALLET_ADDRESS: str
    SYSTEM_PRIVATE_KEY: str

    # ===============================
    # SMART CONTRACT
    # ===============================
    FARM_VERIFICATION_CONTRACT: str

    # ===============================
    # BLOCKCHAIN API (Node.js Express)
    # ===============================
    BLOCKCHAIN_API_URL: str = "http://localhost:3001"


    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
