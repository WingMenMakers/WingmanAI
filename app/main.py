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

from app.core.config import settings

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.requests import Request
from fastapi.responses import RedirectResponse
from wingman_logic.auth.token_manager import save_credentials
from wingman_logic.memory.firestore_memory import FirestoreMemory

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

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=1209600)

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

# 2. Configure Google OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://mail.google.com/ https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive'
    }
)

@app.get("/login/google")
async def login_google(request: Request):
    # This forces the generated URL to use 'https' instead of 'http'
    redirect_uri = request.url_for('auth_callback')
    if "ngrok-free.app" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    
    return await oauth.google.authorize_redirect(
        request, 
        str(redirect_uri), 
        access_type='offline', 
        prompt='consent'
    )

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    if user_info:
        user_email = user_info['email'].lower()
        
        # Explicitly structure the data to ensure Firestore likes it
        creds_to_save = {
            "token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": token.get("scope", "").split(" ")
        }
        
        save_credentials(user_email, "google", creds_to_save)
        request.session['user_email'] = user_email
        return {"status": "Success", "message": "Account linked and tokens saved!"}
    
    return RedirectResponse(url='/login-failed')

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"message": "WingMan API is operational."}

@app.get("/me")
async def check_me(user: Annotated[User, Depends(get_current_user)]):
    """Tell me who is currently logged in based on the session cookie."""
    return {
        "status": "Logged In",
        "email": user.email,
        "name": user.name
    }

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

@app.get("/history", tags=["User Data"])
async def get_chat_history(
    user: Annotated[User, Depends(get_current_user)],
    limit: int = 20
):
    """Retrieves the last N messages for the logged-in user."""
    memory = FirestoreMemory(user_email=user.email)
    # This calls a method we'll ensure is in your FirestoreMemory class
    return memory.get_all_history(limit=limit)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

# --- How to Run ---
# 1. Install dependencies: pip install fastapi uvicorn pydantic python-multipart python-jose[cryptography] google-auth-oauthlib
# 2. Run the application (from the project root directory):
#    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 3. Access the documentation at http://127.0.0.1:8000/docs