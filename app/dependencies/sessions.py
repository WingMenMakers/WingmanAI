# app/dependencies/sessions.py
import logging
from fastapi import Depends, HTTPException, status
from typing import Annotated

from app.schemas.data_contracts import User
from app.core.cache import USER_DIRECTOR_CACHE
from wingman_logic.director import Director
from wingman_logic.memory.firestore_memory import FirestoreMemory
from app.dependencies.auth import get_current_user 
# Use your existing function!
from wingman_logic.auth.token_manager import load_google_credentials, refresh_and_save_if_expired

def get_director_for_user(user: Annotated[User, Depends(get_current_user)]) -> Director:
    user_key = user.email.lower()
    
    # 1. Check cache
    if user_key in USER_DIRECTOR_CACHE:
        return USER_DIRECTOR_CACHE[user_key]
    
    try:
        # 2. Load from Firestore
        google_creds = load_google_credentials(user_key)
        
        # --- IMPORTANT: REFRESH CHECK ---
        # If the token is old, refresh it now before giving it to the Director
        from wingman_logic.auth.token_manager import refresh_and_save_if_expired
        google_creds = refresh_and_save_if_expired(user_key, google_creds)
        
        # 3. Initialize Director
        director_instance = Director(
            user_email=user_key, 
            chat_memory_instance=FirestoreMemory(user_email=user_key),
            google_credentials=google_creds # Make sure your Director class accepts this argument!
        )
        
        USER_DIRECTOR_CACHE[user_key] = director_instance
        return director_instance
        
    except ValueError:
        # This is where your 403 comes from
        raise HTTPException(
            status_code=403, 
            detail="Google account not linked. Please visit /login/google"
        )