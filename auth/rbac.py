from functools import wraps
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from auth.exceptions import ForbiddenAccessException, UnauthorizedAccessException
from auth.dependencies import get_current_user

# ==================== RBAC DECORATOR ====================

def require_role(*allowed_roles):
    """
    Decorator that checks if user has required role.
    
    Usage:
        @require_role("admin")
        async def upload_results(current_user, db):
            # Only admin can reach here
        
        @require_role("admin", "teacher")
        async def get_users(current_user, db):
            # Admin or teacher can reach here
    
    Args:
        *allowed_roles: One or more role strings ("admin", "student", "teacher")
    
    Raises:
        ForbiddenAccessException: If user role not in allowed_roles
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from dependency injection
            # It's passed as kwarg by FastAPI
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise UnauthorizedAccessException()
            
            # Check if user's role is in allowed roles
            if current_user.role not in allowed_roles:
                allowed_str = ", ".join(allowed_roles)
                raise ForbiddenAccessException(
                    f"This action requires one of these roles: {allowed_str}"
                )
            
            # Role is allowed, execute the actual function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ==================== COLLEGE ACCESS CHECK ====================

def ensure_college_access(user, resource_college_id):
    """
    Check if user has access to a specific college.
    
    Args:
        user: Current user object (has college_id)
        resource_college_id: College ID being accessed
    
    Raises:
        ForbiddenAccessException: If user's college != resource's college
    
    Example:
        student = db.query(Student).first()
        ensure_college_access(current_user, student.college_id)
        # If student is from different college → raise exception
    """
    if user.college_id != resource_college_id:
        from auth.exceptions import CollegeAccessViolationException
        raise CollegeAccessViolationException()