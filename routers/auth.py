from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db
from database.models import Student , College
from database.schemas import (
    StudentLoginSchema,
    StudentRegisterSchema,
    RefreshRequest,
    TokenSchema         
)
from auth.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    decode_token
)
from auth.dependencies import get_current_user
from auth.exceptions import InvalidTokenException

router = APIRouter()



# ============================================================================
# 1. LOGIN ENDPOINT
# ============================================================================

@router.post("/login")
async def login(login_data: StudentLoginSchema, db: AsyncSession = Depends(get_db)) -> TokenSchema:
    """
    Student login endpoint
    
    Input: {college_code, roll_no, password}
    Output: {access_token, refresh_token, token_type}
    
    Flow:
    1. Look up college by code in College table
    2. Find student by college_id + roll_no
    3. Verify password
    4. Create tokens
    5. Return tokens
    """
    
    # Step 1: Find college by college_code
    college_query = select(College).where(
        College.college_code == login_data.college_code
    )
    college_result = await db.execute(college_query)
    college = college_result.scalars().first()
    
    if not college:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"College code '{login_data.college_code}' not found"
        )
    
    # Step 2: Find student by college_id + roll_no
    student_query = select(Student).where(
        (Student.college_id == college.id) &
        (Student.roll_no == login_data.roll_no)
    )
    student_result = await db.execute(student_query)
    student = student_result.scalars().first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid roll_no"
        )
    
    # Step 3: Verify password
    if not verify_password(login_data.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Step 4: Create tokens
    payload = {
        "user_id": str(student.roll_no),
        "college_id": str(student.college_id),
        "roll_no": student.roll_no
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    
    # Step 5: Return tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_name": student.name
    }

# ============================================================================
# 2. REFRESH ENDPOINT
# ============================================================================




@router.post("/refresh")
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh endpoint
    
    Input: {refresh_token}
    Output: {access_token, token_type}
    
    Flow:
    1. Validate refresh_token (check signature + expiry)
    2. Find student in DB
    3. Create new access_token
    4. Return new token
    """
    
    # Step 1: Validate refresh_token
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise InvalidTokenException()
    
    # Step 2: Find student in DB
    query = select(Student).where(Student.roll_no == payload.get("user_id"))
    result = await db.execute(query)
    student = result.scalars().first()
    
    if not student:
        raise InvalidTokenException()
    
    # Step 3: Create new access_token
    new_payload = {
        "user_id": str(student.roll_no),
        "college_id": str(student.college_id),
        "roll_no": student.roll_no
    }
    new_access_token = create_access_token(new_payload)
    
    # Step 4: Return new token
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


# ============================================================================
# 3. REGISTER ENDPOINT (Admin only)
# ============================================================================




@router.post("/register")
async def register(
    register_data: StudentRegisterSchema,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register new student (admin only)
    
    Input: {college_id, roll_no, name, email, password}
    Output: {message, student_id}
    
    Flow:
    1. Check: current user is admin?
    2. Check: student already exists?
    3. Hash password
    4. Create new student in DB
    5. Return success
    """
    
    # Step 1: Only admin can register
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can register students"
        )
    
    # Step 2: Student already exists?
    query = select(Student).where(
        (Student.college_id == register_data.college_id) &
        (Student.roll_no == register_data.roll_no)
    )
    result = await db.execute(query)
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student with this roll_no already exists in this college"
        )
    
    # Step 3: Hash password
    hashed_pwd = hash_password(register_data.password)
    
    # Step 4: Create student
    new_student = Student(
        college_id=register_data.college_id,
        roll_no=register_data.roll_no,
        name=register_data.name,
        email=register_data.email,
        password_hash=hashed_pwd,
        role="student"
    )
    
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    
    # Step 5: Return success
    return {
        "message": "Student registered successfully",
        "student_id": str(new_student.id)
    }