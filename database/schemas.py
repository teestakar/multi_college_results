from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum
from datetime import datetime
from uuid import UUID

# ==================== ENUMS ====================
class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    SUPERADMIN = "superadmin"


# ==================== STUDENT SCHEMAS ====================
class StudentRegisterSchema(BaseModel):
    """Schema for student registration"""
    roll_no: str = Field(..., min_length=1, description="Student roll number")
    email: EmailStr  # Validates email format automatically
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: str = Field(..., min_length=1)
    degree: str  # B.Tech, M.Tech, etc
    branch: str  # CSE, ECE, etc
    year: int = Field(..., ge=1, le=4)  # 1, 2, 3, or 4

class StudentLoginSchema(BaseModel):
    """Schema for student login"""
    college_code: str = Field(..., min_length=1)  # ← ADD THIS
    roll_no: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class StudentResponseSchema(BaseModel):
    """Schema for returning student data (no password!)"""
    roll_no: str
    email: str
    name: str
    degree: str
    branch: str
    year: int
    
    class Config:
        from_attributes = True  # Convert ORM object to schema


# ==================== TEACHER SCHEMAS ====================
class TeacherRegisterSchema(BaseModel):
    """Schema for teacher registration (admin only)"""
    teacher_id: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)


class TeacherLoginSchema(BaseModel):
    """Schema for teacher login"""
    teacher_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TeacherResponseSchema(BaseModel):
    """Schema for returning teacher data (no password!)"""
    teacher_id: str
    email: str
    name: str
    
    class Config:
        from_attributes = True


# ==================== TOKEN SCHEMAS ====================
class TokenSchema(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"  # Always "bearer"
    refresh_token: Optional[str] = None
    user_name: str 


class TokenDataSchema(BaseModel):
    """Schema for data inside JWT token"""
    user_id: str  # roll_no for students, teacher_id for teachers
    user_type: str  # "student" or "teacher"
    college_id: str

class RefreshRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., min_length=1)


# ==================== GENERIC SCHEMAS ====================
class MessageSchema(BaseModel):
    """Generic message response"""
    message: str
    status: str  # "success", "error"


class ErrorSchema(BaseModel):
    """Generic error response"""
    detail: str
    status_code: int


# ==================== MARK/RESULTS SCHEMAS ====================
class MarkResponseSchema(BaseModel):
    """Schema for a single mark/result"""
    id: UUID
    semester: int
    subject_code: str
    subject_name: str
    grade: str
    points: float
    credits: float
    credit_points: float
    uploaded_at: datetime  # ISO format datetime
    
    class Config:
        from_attributes = True  # Convert ORM object to schema


class ResultsResponseSchema(BaseModel):
    """Schema for results list response"""
    results: list[MarkResponseSchema]
    total_count: int  # Total marks in the filtered query
    limit: int  # How many per page
    offset: int  # Starting position
    semester: Optional[int] = None  # Which semester was filtered (if any)
    message: str = "Results fetched successfully"


class ResultStatisticsSchema(BaseModel):
    """Schema for result statistics (admin view)"""
    total_marks: int  # How many marks does student have
    avg_points: float  # Average grade points
    pass_count: int  # How many marks >= 5.0 (passing)
    fail_count: int  # How many marks < 5.0 (failing)
    by_semester: dict  # {1: avg_points, 2: avg_points, ...}

# ==================== COLLEGE + ADMIN SCHEMAS ====================
class CollegeAdminRegisterSchema(BaseModel):
    """Schema for college registration with first admin"""
    college_code: str = Field(..., min_length=1, max_length=10, description="Unique college code (e.g., IEM, VIT)")
    college_name: str = Field(..., min_length=1, description="Full college name")
    admin_name: str = Field(..., min_length=1, description="Admin full name")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class CollegeAdminResponseSchema(BaseModel):
    """Response after college + admin registration"""
    message: str
    status: str = "success"
    college_id: str
    admin_id: str