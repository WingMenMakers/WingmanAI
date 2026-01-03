from fastapi import Request, HTTPException, status
from app.schemas.data_contracts import User

async def get_current_user(request: Request) -> User:
    email = request.session.get('user_email')
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not logged in."
        )
        
    # Add the 'name' field here to satisfy the Pydantic User model
    return User(
        email=email, 
        uid=email, 
        name=email.split('@')[0]  # Uses the first part of email as a temporary name
    )