# wingman_logic/auth/token_manager.py

import logging
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from app.core.config import settings
from google.auth.transport.requests import Request as GoogleRequest
from app.core.config import db

def save_credentials(email: str, service: str, data: Dict[str, Any]):
    """Saves or updates a user's credentials for a specific service in Firestore."""
    user_key = email.lower()
    doc_ref = db.collection("wingman_users").document(user_key)
    
    # We use 'merge=True' so we don't overwrite other services (like LinkedIn) 
    # when saving Google creds.
    doc_ref.set({
        "email": user_key,
        "services": {
            service: data
        }
    }, merge=True)
    
    logging.info(f"✅ Credentials for '{service}' saved to Firestore for {email}.")

def load_google_credentials(user_email: str) -> Credentials:
    user_key = user_email.lower()
    # 1. Check if the collection name matches exactly what you used in save_credentials
    doc = db.collection("wingman_users").document(user_key).get()

    if doc.exists:
        data = doc.to_dict()
        # 2. Your save_credentials puts it inside a "services" -> "google" map
        services = data.get("services", {})
        google_data = services.get("google")
        
        if google_data:
            # This converts the dict back into a Google Auth object
            return Credentials.from_authorized_user_info(google_data)
    
    # If it reaches here, it raises the error you saw
    raise ValueError(f"No Google credentials found")

def load_linkedin_tokens(email: str) -> Dict[str, Any]:
    """Loads LinkedIn token data from Firestore."""
    user_key = email.lower()
    doc = db.collection("wingman_users").document(user_key).get()
    
    if not doc.exists:
        raise ValueError(f"User {email} not found in Firestore.")
    
    linkedin_data = doc.to_dict().get("services", {}).get("linkedin")
    if not linkedin_data:
        raise ValueError(f"LinkedIn tokens not found in Firestore for {email}.")
        
    return linkedin_data

def has_scope(user_email, required_scope):
    """Checks if a user has authorized a specific Google scope via Firestore."""
    try:
        user_key = user_email.lower()
        doc = db.collection("wingman_users").document(user_key).get()
        if not doc.exists: return False
        
        google_data = doc.to_dict().get("services", {}).get("google", {})
        return required_scope in google_data.get("scopes", [])
    except Exception:
        return False

def refresh_and_save_if_expired(user_email: str, creds: Credentials):
    """Checks if token is expired, refreshes it, and saves the new one back to Firestore."""
    if creds.expired and creds.refresh_token:
        logging.info(f"🔄 Token expired for {user_email}. Refreshing...")
        creds.refresh(GoogleRequest())
        
        # Convert back to dict to save
        updated_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        # Save back to Firestore so the NEXT session uses the new token
        save_credentials(user_email, "google", updated_data)
        logging.info(f"✅ Refreshed token saved for {user_email}")
    return creds