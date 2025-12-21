from fastapi import Depends, HTTPException, status
# 🎯 CORRECT FIX: Import the standard HTTPBearer scheme
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from app.schemas.data_contracts import User # Import the Pydantic User model

# Initialize the Bearer scheme for Swagger/OpenAPI documentation
# It enforces the Authorization: Bearer <token> format.
security_scheme = HTTPBearer(auto_error=False) # auto_error=False lets us handle the 401 manually

async def get_current_user(
    # Get the credentials object (which contains the token) from the security scheme
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]
) -> User:
    """
    Authenticates the user via the Firebase ID Token and returns the validated User object.
    
    :param credentials: The object containing the scheme ("Bearer") and the token string.
    :raises HTTPException 401: If the token is invalid, missing, or expired.
    :return: A validated User Pydantic model.
    """
    
    # Check if credentials were provided at all
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Extract the token string from the credentials object
    token = credentials.credentials.lower() 
    
    # --- STEP 1: Placeholder for REAL Firebase Verification ---
    # In a real application, you would use:
    # try:
    #     decoded_token = await firebase_admin.auth.verify_id_token(token)
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid or expired authentication token.",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )

    # --- STEP 2: Mocking the Verified User Data for Execution ---
    mock_email = token 
    
    if "testuser@example.com" in mock_email:
        # User 1: Valid
        return User(
            uid="fbs_uid_7890", 
            email="testuser@example.com", 
            name="Test User"
        )
    elif "testuser2@example.com" in mock_email:
        # User 2: Valid
        return User(
            uid="fbs_uid_1234", 
            email="testuser2@example.com", 
            name="Second User"
        )
    else:
        # Default failure for any other token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )