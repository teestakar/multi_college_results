from fastapi import HTTPException, status

# ==================== AUTHENTICATION ERRORS ====================

class InvalidCredentialsException(HTTPException):
    """User provided wrong password or invalid roll_no"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid roll_no or password"
        )


class TokenExpiredException(HTTPException):
    """JWT token has expired"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again."
        )


class InvalidTokenException(HTTPException):
    """JWT token is invalid or malformed"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ==================== AUTHORIZATION ERRORS ====================

class UnauthorizedAccessException(HTTPException):
    """User is not logged in or token is missing"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )


class ForbiddenAccessException(HTTPException):
    """User doesn't have permission (role check failed)"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


class CollegeAccessViolationException(HTTPException):
    """User trying to access another college's data"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this college's data"
        )


# ==================== RESOURCE ERRORS ====================

class ResourceNotFoundException(HTTPException):
    """Resource doesn't exist (user, result, etc)"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )


class ResourceAlreadyExistsException(HTTPException):
    """Resource already exists (duplicate email, roll_no)"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} already exists"
        )


# ==================== VALIDATION ERRORS ====================

class InvalidInputException(HTTPException):
    """User input is invalid (wrong format, out of range)"""
    def __init__(self, message: str = "Invalid input"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )