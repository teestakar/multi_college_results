from fastapi import HTTPException, status

# ==================== AUTHENTICATION ERRORS ====================

class InvalidCredentialsException(HTTPException):
    """User provided wrong password or invalid roll_no"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid roll_no or password",
                "details": None
            }
        )


class InvalidTeacherCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid teacher ID or password",
                "details": None
            }
        )


class TokenExpiredException(HTTPException):
    """JWT token has expired"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "code": "TOKEN_EXPIRED",
                "message": "Token has expired. Please login again.",
                "details": None
            }
        )


class InvalidTokenException(HTTPException):
    """JWT token is invalid or malformed"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "code": "INVALID_TOKEN",
                "message": "Invalid token",
                "details": None
            }
        )


# ==================== AUTHORIZATION ERRORS ====================

class UnauthorizedAccessException(HTTPException):
    """User is not logged in or token is missing"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "code": "NOT_AUTHENTICATED",
                "message": "Not authenticated",
                "details": None
            }
        )


class ForbiddenAccessException(HTTPException):
    """User doesn't have permission (role check failed)"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "code": "ACCESS_DENIED",
                "message": message,
                "details": None
            }
        )


class AdminOnlyException(HTTPException):
    """Only admins can perform this action"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "code": "ADMIN_ONLY",
                "message": "Only admins can perform this action",
                "details": None
            }
        )


class CollegeAccessViolationException(HTTPException):
    """User trying to access another college's data"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "code": "COLLEGE_ACCESS_VIOLATION",
                "message": "You don't have access to this college's data",
                "details": None
            }
        )


# ==================== RESOURCE ERRORS ====================

class ResourceNotFoundException(HTTPException):
    """Resource doesn't exist (user, result, etc)"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "error",
                "code": "RESOURCE_NOT_FOUND",
                "message": f"{resource} not found",
                "details": None
            }
        )


class ResourceAlreadyExistsException(HTTPException):
    """Resource already exists (duplicate email, roll_no)"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "error",
                "code": "RESOURCE_ALREADY_EXISTS",
                "message": f"{resource} already exists",
                "details": None
            }
        )


# ==================== VALIDATION ERRORS ====================

class InvalidInputException(HTTPException):
    """User input is invalid (wrong format, out of range)"""
    def __init__(self, message: str = "Invalid input", details: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "code": "INVALID_INPUT",
                "message": message,
                "details": details
            }
        )


# ==================== CSV ERRORS ====================

class CSVParseError(HTTPException):
    """Failed to parse CSV file"""
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "code": "CSV_PARSE_ERROR",
                "message": "Failed to parse CSV file",
                "details": details
            }
        )


class CSVHeaderMismatchError(HTTPException):
    """CSV header format is incorrect"""
    def __init__(self, missing: set = None, extra: set = None):
        details = ""
        if missing:
            details += f"Missing columns: {', '.join(missing)}. "
        if extra:
            details += f"Extra columns: {', '.join(extra)}"
        
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "code": "CSV_HEADER_MISMATCH",
                "message": "CSV header format is incorrect",
                "details": details.strip() if details.strip() else None
            }
        )


class CSVProcessingError(HTTPException):
    """Error during CSV processing"""
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "error",
                "code": "CSV_PROCESSING_ERROR",
                "message": "Error processing CSV file",
                "details": details
            }
        )


# ==================== SERVER ERRORS ====================

class DatabaseError(HTTPException):
    """Database operation failed"""
    def __init__(self, details: str = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "code": "DATABASE_ERROR",
                "message": "Database operation failed",
                "details": details
            }
        )