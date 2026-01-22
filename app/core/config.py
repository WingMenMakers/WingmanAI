# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from typing import Optional
from google.cloud import firestore

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Core Application Settings
    APP_NAME: str = "WingMan FastAPI"
    APP_VERSION: str = "1.0.0"
    
    # 🎯 NEW: Required for SessionMiddleware (encrypts cookies)
    SECRET_KEY: str = Field(..., description="Secret key for signing session cookies.")
    
    # --- External API Keys (.env) ---
    OPENAI_API_KEY: str = Field(..., description="API key for OpenAI calls.")
    TAVILY_API_KEY: Optional[str] = Field(None, description="API key for the Websearch Agent (Tavily).")
    
    # --- Google OAuth Settings (.env) ---
    # 🎯 NEW: Required for the /login/google flow
    GOOGLE_CLIENT_ID: str = Field(..., description="Google OAuth Client ID.")
    GOOGLE_CLIENT_SECRET: str = Field(..., description="Google OAuth Client Secret.")
    
    # --- Google/Firebase Settings (.env) ---
    # Path to service_account.json for Firestore access
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/service_account.json")

    # --- Local File Paths ---
    # We keep these for now, but as we move to Firestore, these will eventually become obsolete
    USERS_FILE_PATH: str = "data/users.json"
    CLIENT_SECRET_PATH: str = "config/client_secret.json"
    SCOPES_FILE_PATH: str = "config/scopes.json"
    FRONTEND_URL: str = Field("http://localhost:5173", description="Frontend application URL for redirects.")

# Create a singleton settings instance
settings = Settings()

db = firestore.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)