# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from typing import Optional

# Ensure python-dotenv is installed: pip install python-dotenv pydantic-settings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Core Application Settings
    APP_NAME: str = "WingMan FastAPI"
    APP_VERSION: str = "1.0.0"
    
    # --- External API Keys (.env) ---
    OPENAI_API_KEY: str = Field(..., description="API key for OpenAI calls.")
    TAVILY_API_KEY: Optional[str] = Field(None, description="API key for the Websearch Agent (Tavily).")
    
    # --- Google/Firebase Settings (.env) ---
    # This is set for the FirestoreMemory service account (for production)
    # The value is usually the path to the service account JSON key.
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # --- Local File Paths (Relative to token_manager or Director) ---
    # NOTE: These paths must be correct relative to the calling script (token_manager.py)
    # We define them here for central access, but the OS file calls remain local to the token manager.
    USERS_FILE_PATH: str = "data/users.json"
    CLIENT_SECRET_PATH: str = ".config/client_secret.json"
    SCOPES_FILE_PATH: str = ".config/scopes.json"

# Create a singleton settings instance
settings = Settings()