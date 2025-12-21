# app/schemas/data_contracts.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Dict, List

# --- 1. Output of the Auth Dependency (Internal User Model) ---
class User(BaseModel):
    """Represents the validated user identity from the Firebase ID Token."""
    uid: str = Field(..., description="The unique Firebase User ID.")
    email: EmailStr = Field(..., description="The user's verified email address, used as the Director cache key.")
    name: str = Field(..., description="The user's display name.")

# --- 2. Input body for the /query endpoint ---
class QueryRequest(BaseModel):
    """The input body for the Director endpoint."""
    query: str = Field(..., min_length=1, description="The user's conversational request to WingMan.")

# --- 3. Output body of the /query endpoint (The final Director contract) ---
class DirectorResponse(BaseModel):
    """The final structured response from the Director Orchestrator."""
    message: str = Field(..., description="The final, human-readable conversational response for the user.")
    raw_data: Optional[Any] = Field(None, description="The raw, unformatted data object (list/dict) from the final executing agent, if applicable.")
    agent_key: Optional[str] = Field(None, description="The key of the last agent used (e.g., 'email', 'self', 'websearch').")