# app/dependencies/sessions.py

import logging
from fastapi import Depends, HTTPException, status
from typing import Annotated

from app.schemas.data_contracts import User
from app.core.cache import USER_DIRECTOR_CACHE
from wingman_logic.director import Director
from wingman_logic.memory.firestore_memory import FirestoreMemory

# Dependency 1 (Input for this function)
from app.dependencies.auth import get_current_user 

def get_director_for_user(user: Annotated[User, Depends(get_current_user)]) -> Director:
    """
    Retrieves or initializes a stateful Director instance. 
    Ensures absolute state isolation between users by partitioning memory and logic.
    """
    
    # 1. Standardize the key to prevent "User@gmail.com" and "user@gmail.com" collisions.
    user_key = user.email.lower()
    
    # 2. Check the Global Cache (State Isolation Check)
    if user_key in USER_DIRECTOR_CACHE:
        logging.info(f"🚀 Cache HIT: Retrieving active session for {user_key}")
        return USER_DIRECTOR_CACHE[user_key]
    
    # 3. Cache MISS: Build a new isolated workspace for this specific user
    logging.info(f"🛡️ Cache MISS: Creating isolated workspace for {user_key}")
    
    try:
        # STEP A: Create the User-Specific Memory Engine.
        # This instance loads ONLY {user_email}_memory.json.
        # It contains the new 'trace' and 'get_focused_context' logic.
        memory_instance = FirestoreMemory(user_email=user_key)
        
        # STEP B: Instantiate the Director.
        # We inject the memory_instance here. 
        # Inside Director.__init__, it will now use this instance to fetch context 
        # for its dynamic planner without ever seeing other users' data.
        director_instance = Director(
            user_email=user_key, 
            chat_memory_instance=memory_instance
        )
        
        # STEP C: Cache for subsequent requests.
        # This persists the Director's 'pending_task_plan' (interruption state) 
        # so User A can answer a question 5 minutes later and resume correctly.
        USER_DIRECTOR_CACHE[user_key] = director_instance
        
        logging.info(f"✅ Isolated Director & Memory ready for {user_key}.")
        return director_instance
        
    except ValueError as e:
        # This handles the case where users exist in Firebase but haven't 
        # linked Google/LinkedIn services yet (missing from data/users.json).
        logging.warning(f"⚠️ Auth mapping failed for {user_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service credentials not found. Please run login.py first. Error: {str(e)}",
        )
    except Exception as e:
        logging.error(f"🔥 Critical Failure during session setup for {user_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not establish a secure user session."
        )
    