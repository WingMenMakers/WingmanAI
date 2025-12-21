# app/main.py

import logging
import sys
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from asyncio import to_thread # Import for running sync code in the async context

# Import Pydantic models (Data Contracts)
from app.schemas.data_contracts import User, QueryRequest, DirectorResponse
# Import Dependencies
from app.dependencies.auth import get_current_user
from app.dependencies.sessions import get_director_for_user
# Import the Director Orchestrator class
from wingman_logic.director import Director 

# --- Logging Configuration (Replicated from old main.py) ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="WingMan Multi-Agent API",
    description="Asynchronous API orchestrating agents with per-user state isolation.",
    version="1.0.0"
)

# 1. CORS Middleware Setup
# IMPORTANT: Adjust 'allow_origins' to your actual frontend URL in production!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes ---

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"message": "WingMan API is operational."}

@app.post(
    "/query", 
    response_model=DirectorResponse, 
    tags=["Agent Orchestration"],
    summary="Process a user query using the Director and specialized agents."
)
async def process_query(
    request_data: QueryRequest,
    director: Annotated[Director, Depends(get_director_for_user)],
    user: Annotated[User, Depends(get_current_user)] # Dependency is run but the result is just for logging/debugging
):
    """
    The core asynchronous route that takes a user query, retrieves the per-user 
    Director instance, executes the synchronous business logic in a separate 
    thread, and returns the structured response.
    """
    logging.info(f"API Request from {user.email}: '{request_data.query}'")
    
    try:
        # The director.handle_query() method contains CPU-bound/synchronous LLM calls 
        # (OpenAI, token_manager.py file access, agent execution).
        # We must run it in a separate thread using asyncio.to_thread 
        # to prevent blocking the main FastAPI event loop, ensuring true asynchronous behavior.
        
        # NOTE: We skip the redundant copying of conversation history (from old main.py)
        # because the Director already has the chat_memory instance injected.
        
        director_output = await to_thread(director.handle_query, request_data.query)
        
        # director_output is guaranteed to be a dict matching the DirectorResponse structure
        return DirectorResponse(
            message=director_output.get("message", "Internal error: No message returned."),
            raw_data=director_output.get("raw_data"),
            agent_key=director_output.get("agent_key")
        )
        
    except HTTPException:
        # Re-raise explicit HTTPExceptions (e.g., from dependencies)
        raise
    except Exception as e:
        logging.error(f"Director Execution Error for {user.email}: {e}", exc_info=True)
        # Catch-all for unexpected Director errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during query processing: {str(e)}",
        )

# --- How to Run ---
# 1. Install dependencies: pip install fastapi uvicorn pydantic python-multipart python-jose[cryptography] google-auth-oauthlib
# 2. Run the application (from the project root directory):
#    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 3. Access the documentation at http://127.0.0.1:8000/docs