from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from database.database import get_db
from database.models import Student
from auth.auth import decode_token
from auth.exceptions import InvalidTokenException, TokenExpiredException

security = HTTPBearer()


async def get_current_user(
    credentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Student:
    """
    Extract and validate the current user from JWT token.
    
    This dependency is used on every protected endpoint.
    It verifies the token is valid, not expired, and finds the student in DB.
    
    Args:
        credentials: Token from Authorization header
        db: Database session
    
    Returns:
        Student object (current user)
    
    Raises:
        InvalidTokenException: If token is invalid or expired
    
    Example usage in endpoint:
        @router.get("/api/results/me")
        async def get_my_results(current_user = Depends(get_current_user)):
            # current_user is now the Student object
            return results for current_user
    """
    token = credentials.credentials
    
    try:
        # Decode token (verify signature + expiry)
        payload = decode_token(token)
    except JWTError:
        raise InvalidTokenException()
    
    # Extract user_id (roll_no) and college_id from token
    user_id: str = payload.get("user_id")
    college_id: str = payload.get("college_id")
    
    if not user_id or not college_id:
        raise InvalidTokenException()
    
    # Find student in database
    result = await db.execute(
        select(Student).where(
            (Student.roll_no == user_id) &
            (Student.college_id == college_id)
        )
    )
    student = result.scalars().first()
    
    if not student:
        raise InvalidTokenException()
    
    return student