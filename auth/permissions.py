# auth/permissions.py

from fastapi import Depends
from database.models import Student, Teacher
from auth.dependencies import get_current_user
from auth.exceptions import (
    UnauthorizedAccessException,
    AdminOnlyException
)

# ==================== PERMISSIONS DEFINITION ====================
"""
This is the SOURCE OF TRUTH for what each role can do.

STUDENT:
  - view_own_results: Can see their own marks/results

TEACHER:
  - upload_csv: Can upload marks for their subject
  - view_own_stats: Can see statistics of only their uploads

ADMIN:
  - approve_uploads: Can review and approve pending uploads
  - view_all_stats: Can see college-wide statistics
"""

PERMISSIONS = {
    "student": [
        "view_own_results",
    ],
    "teacher": [
        "upload_csv",
        "view_own_stats",
    ],
    "admin": [
        "approve_uploads",
        "view_all_stats",
    ]
}


# ==================== DECORATORS ====================

def require_student(current_user=Depends(get_current_user)):
    """
    Check if user is a STUDENT.
    
    Raises:
        UnauthorizedAccessException: If user is not a student
    
    Returns:
        Student: The current student user
    
    Example:
        @router.get("/results/me")
        async def get_results(current_user = Depends(require_student)):
            # current_user is guaranteed to be Student
            return student_results
    """
    if not isinstance(current_user, Student):
        raise UnauthorizedAccessException()
    
    return current_user


def require_teacher(current_user=Depends(get_current_user)):
    """
    Check if user is a TEACHER or ADMIN.
    
    Why "or admin"? 
    - Admins can do everything teachers can do
    - So if you need teacher permission, admin also qualifies
    
    Raises:
        UnauthorizedAccessException: If user is not a teacher or admin
    
    Returns:
        Teacher: The current teacher user
    
    Example:
        @router.post("/results/upload-csv")
        async def upload_csv(current_user = Depends(require_teacher)):
            # current_user is guaranteed to be Teacher or Admin
            return upload_result
    """
    if not isinstance(current_user, Teacher):
        raise UnauthorizedAccessException()
    
    if current_user.role not in ["teacher", "admin"]:
        raise UnauthorizedAccessException()
    
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    """
    Check if user is an ADMIN.
    
    Only admins can approve uploads, manage users, etc.
    
    Raises:
        UnauthorizedAccessException: If user is not a teacher
        AdminOnlyException: If user is teacher but not admin
    
    Returns:
        Teacher: The current admin user (as Teacher model with role="admin")
    
    Example:
        @router.post("/approvals/approve")
        async def approve_upload(current_user = Depends(require_admin)):
            # current_user is guaranteed to be Admin
            return approval_result
    """
    if not isinstance(current_user, Teacher):
        raise UnauthorizedAccessException()
    
    if current_user.role != "admin":
        raise AdminOnlyException()
    
    return current_user