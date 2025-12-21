# app/core/cache.py

from typing import Dict, Optional
import logging
import asyncio

# Assuming Director and FirestoreMemory are correctly located
from wingman_logic.director import Director 
from wingman_logic.memory.firestore_memory import FirestoreMemory
from app.schemas.data_contracts import User

# --- GLOBAL STATE (The Cache) ---
# Maps user email (unique identifier) to the active Director instance.
USER_DIRECTOR_CACHE: Dict[str, Director] = {}
logging.info("Initialized global USER_DIRECTOR_CACHE.")