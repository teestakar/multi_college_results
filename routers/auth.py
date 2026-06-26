from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db
from database.models import Student , College, Teacher, Degree, Branch
from database.schemas import (
    StudentLoginSchema,
    StudentRegisterSchema,
    RefreshRequest,
    TokenSchema,
    MessageSchema,  # ← ADD THIS
    CollegeAdminRegisterSchema,          # ← ADD THIS
    CollegeAdminResponseSchema,
    TeacherLoginSchema,           # ← ADD THIS
    TeacherRegisterSchema
)
from auth.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    decode_token
)
from auth.dependencies import get_current_user
from auth.permissions import require_admin
from auth.exceptions import (
    InvalidCredentialsException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidTokenException,
    InvalidTeacherCredentialsException
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# ============================================================================
# 0. COLLEGE + ADMIN REGISTRATION (Anyone can do this) (UPDATED)
# ============================================================================

from auth.exceptions import ResourceAlreadyExistsException  # ← ADD THIS

@router.post("/college-register")
@limiter.limit("3/hour")
async def register_college_and_admin(
    request: Request, 
    register_data: CollegeAdminRegisterSchema,
    db: AsyncSession = Depends(get_db)) -> CollegeAdminResponseSchema:

    """
    Register a new college and create the first admin
    
    Input: {college_code, college_name, admin_name, admin_email, admin_password}
    Output: {message, status, college_id, admin_id}
    
    Flow:
    1. Check: college_code already exists?
    2. Create College
    3. Hash admin password
    4. Create Admin (as Teacher with role="admin")
    5. Return success with IDs
    """
    
    # Step 1: College code already exists?
    college_query = select(College).where(
        College.college_code == register_data.college_code
    )
    college_result = await db.execute(college_query)
    existing_college = college_result.scalars().first()
    
    # ← CHANGED: Use custom exception instead of HTTPException
    if existing_college:
        raise ResourceAlreadyExistsException(f"College code '{register_data.college_code}'")
    
    # Step 2: Create College
    new_college = College(
        name=register_data.college_name,
        college_code=register_data.college_code
    )
    db.add(new_college)
    await db.flush()  # ← Flush to get the college.id without committing
    
    # Step 3: Hash admin password
    hashed_pwd = hash_password(register_data.admin_password)
    
    # Step 4: Create Admin (Teacher with role="admin")
    # Use college_code as teacher_id for admin (e.g., "IEM_ADMIN")
    admin_teacher_id = f"{register_data.college_code}_ADMIN"
    
    new_admin = Teacher(
        teacher_id=admin_teacher_id,
        name=register_data.admin_name,
        email=register_data.admin_email,
        password_hash=hashed_pwd,
        college_id=new_college.id,
        role="admin"  # ← Mark as admin
    )
    db.add(new_admin)
    
    # Step 5: Commit both
    await db.commit()
    await db.refresh(new_college)
    await db.refresh(new_admin)
    
    # Step 6: Return success
    return CollegeAdminResponseSchema(
        message=f"College '{register_data.college_name}' registered successfully. Admin account created.",
        status="success",
        college_id=str(new_college.id),
        admin_id=admin_teacher_id
    )


@router.get("/colleges")
async def get_colleges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(College)
    )

    colleges = result.scalars().all()

    return [
        {
            "code": college.college_code,
            "name": college.name
        }
        for college in colleges
    ]



# ============================================================================
# 1. LOGIN ENDPOINT (UPDATED)
# ============================================================================

from auth.exceptions import InvalidCredentialsException, ResourceNotFoundException  # ← ADD THESE

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, login_data: StudentLoginSchema, db: AsyncSession = Depends(get_db)) -> TokenSchema:
    """
    Student login endpoint
    
    Input: {college_code, roll_no, password}
    Output: {access_token, refresh_token, token_type, user_name}
    """
    
    # Step 1: Find college by college_code
    college_query = select(College).where(
        College.college_code == login_data.college_code
    )
    college_result = await db.execute(college_query)
    college = college_result.scalars().first()
    
    # ← CHANGED: Use custom exception instead of HTTPException
    if not college:
        raise ResourceNotFoundException("College")
    
    # Step 2: Find student by college_id + roll_no
    student_query = select(Student).where(
        (Student.college_id == college.id) &
        (Student.roll_no == login_data.roll_no)
    )
    student_result = await db.execute(student_query)
    student = student_result.scalars().first()
    
    # ← CHANGED: Use custom exception instead of HTTPException
    if not student:
        raise InvalidCredentialsException()
    
    # Step 3: Verify password
    if not verify_password(login_data.password, student.password_hash):
        # ← CHANGED: Use custom exception instead of HTTPException
        raise InvalidCredentialsException()
    
    # Step 4: Create tokens
    payload = {
        "user_id": str(student.roll_no),
        "user_type": "student", 
        "college_id": str(student.college_id)
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    
    # Step 5: Return tokens (explicitly create schema)
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_name=student.name
    )

# ============================================================================
# 2. REFRESH ENDPOINT
# ============================================================================

@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request, request_data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenSchema:
    """
    Refresh endpoint
    
    Input: {refresh_token}
    Output: {access_token, token_type}
    """
    
    # Step 1: Validate refresh_token
    try:
        payload = decode_token(request_data.refresh_token)
    except Exception:
        raise InvalidTokenException()
    
    # Step 2: Find user in DB (student or teacher)
    user_id = payload.get("user_id")
    college_id = payload.get("college_id")
    user_type = payload.get("user_type")

    if not user_id or not college_id or not user_type:
        raise InvalidTokenException()

    if user_type == "teacher":
        result = await db.execute(
            select(Teacher).where(
                (Teacher.teacher_id == user_id) &
                (Teacher.college_id == college_id)
            )
        )
    elif user_type == "student":
        result = await db.execute(
            select(Student).where(
                (Student.roll_no == user_id) &
                (Student.college_id == college_id)
            )
        )
    else:
        raise InvalidTokenException()

    user = result.scalars().first()
    if not user:
        raise InvalidTokenException()

    # Step 3: Create new access_token
    new_payload = {
        "user_id": str(user_id),
        "user_type": user_type,
        "college_id": str(college_id)
    }
    new_access_token = create_access_token(new_payload)
    
    # Step 4: Return new token (explicitly create schema)
    return TokenSchema(
        access_token=new_access_token,
        token_type="bearer",
        user_name=user.name 
    )


# ============================================================================
# STUDENT REGISTRATION ENDPOINT (Admin only) (UPDATED)
# ============================================================================

@router.post("/register")
@limiter.limit("20/hour")
async def register_student(
    request: Request,
    register_data: StudentRegisterSchema, 
    current_user: Teacher = Depends(require_admin),  # ← CHANGED: Use require_admin!
    db: AsyncSession = Depends(get_db)) -> MessageSchema:
    """
    Register new student (admin only)
    
    Input: {roll_no, name, email, password, degree, branch, year}
    Output: {message, status}
    """
    
    # ← REMOVED: No need to check role here anymore!
    # if current_user.role != "admin":
    #     raise AdminOnlyException()
    
    # Step 2: Student already exists in this college?
    query = select(Student).where(
        (Student.college_id == current_user.college_id) &
        (Student.roll_no == register_data.roll_no)
    )
    result = await db.execute(query)
    existing = result.scalars().first()
    
    if existing:
        raise ResourceAlreadyExistsException(f"Student {register_data.roll_no}")
    
    # Step 3: Auto-create or fetch DEGREE
    degree_query = select(Degree).where(
        (Degree.college_id == current_user.college_id) &
        (Degree.name == register_data.degree)
    )
    degree_result = await db.execute(degree_query)
    degree_obj = degree_result.scalars().first()
    
    if not degree_obj:
        degree_obj = Degree(
            college_id=current_user.college_id,
            name=register_data.degree
        )
        db.add(degree_obj)
        await db.flush()
        print(f"DEBUG: Created new degree: {register_data.degree}")
    else:
        print(f"DEBUG: Using existing degree: {register_data.degree}")
    
    # Step 4: Auto-create or fetch BRANCH
    branch_query = select(Branch).where(
        (Branch.degree_id == degree_obj.id) &
        (Branch.college_id == current_user.college_id) &
        (Branch.name == register_data.branch)
    )
    branch_result = await db.execute(branch_query)
    branch_obj = branch_result.scalars().first()
    
    if not branch_obj:
        branch_obj = Branch(
            degree_id=degree_obj.id,
            college_id=current_user.college_id,
            name=register_data.branch
        )
        db.add(branch_obj)
        await db.flush()
        print(f"DEBUG: Created new branch: {register_data.branch} for degree {register_data.degree}")
    else:
        print(f"DEBUG: Using existing branch: {register_data.branch}")
    
    # Step 5: Hash password
    hashed_pwd = hash_password(register_data.password)
    
    # Step 6: Create student with degree + branch
    new_student = Student(
        roll_no=register_data.roll_no,
        name=register_data.name,
        email=register_data.email,
        password_hash=hashed_pwd,
        degree_id=degree_obj.id,
        branch_id=branch_obj.id,
        year=register_data.year,
        college_id=current_user.college_id
    )
    
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    
    # Step 7: Return success
    return MessageSchema(
        message=f"Student '{register_data.roll_no}' ({register_data.degree}, {register_data.branch}, Batch {register_data.year}) registered successfully",
        status="success"
    )

# ============================================================================
# TEACHER LOGIN ENDPOINT (UPDATED)
# ============================================================================

@router.post("/teacher/login")
@limiter.limit("5/minute")
async def teacher_login(request: Request, login_data: TeacherLoginSchema, db: AsyncSession = Depends(get_db)) -> TokenSchema:
    """
    Teacher login endpoint
    
    Input: {teacher_id, password}
    Output: {access_token, refresh_token, token_type, user_name}
    """
    
    # Step 1: Find teacher by teacher_id
    teacher_query = select(Teacher).where(
        Teacher.teacher_id == login_data.teacher_id
    )
    teacher_result = await db.execute(teacher_query)
    teacher = teacher_result.scalars().first()
    
    # ← CHANGED: Use custom exception instead of HTTPException
    if not teacher:
        raise InvalidTeacherCredentialsException()
    
    # Step 2: Verify password
    if not verify_password(login_data.password, teacher.password_hash):
        # ← CHANGED: Use custom exception instead of HTTPException
        raise InvalidTeacherCredentialsException()
    
    # Step 3: Create tokens
    payload = {
        "user_id": str(teacher.teacher_id),
        "user_type": "teacher",
        "college_id": str(teacher.college_id)
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    
    # Step 4: Return tokens
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_name=teacher.name
    )

# ============================================================================
# TEACHER role endpoint
# ============================================================================
from sqlalchemy import select
from database.models import College

@router.get("/teacher/me")
async def get_teacher_profile(
    current_user: Teacher = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(College).where(
            College.id == current_user.college_id
        )
    )

    college = result.scalar_one_or_none()

    return {
        "teacher_id": current_user.teacher_id,
        "name": current_user.name,
        "role": current_user.role,
        "college_id": str(current_user.college_id),
        "college_name": college.name if college else "Unknown"
    }



# ============================================================================
# TEACHER REGISTRATION ENDPOINT (Admin only) (UPDATED)
# ============================================================================

@router.post("/teacher/register")
@limiter.limit("20/hour")
async def register_teacher(
    request: Request, 
    register_data: TeacherRegisterSchema, 
    current_user: Teacher = Depends(require_admin),  # ← CHANGED: Use require_admin!
    db: AsyncSession = Depends(get_db)) -> MessageSchema:
    
    """
    Register new teacher (admin only)
    
    Input: {teacher_id, password, name, email}
    Output: {message, status}
    """
    
    # ← REMOVED: No need to check role here anymore!
    # if current_user.role != "admin":
    #     raise AdminOnlyException()
    
    # Step 2: Teacher already exists?
    query = select(Teacher).where(
        Teacher.teacher_id == register_data.teacher_id
    )
    result = await db.execute(query)
    existing = result.scalars().first()
    
    if existing:
        raise ResourceAlreadyExistsException(f"Teacher {register_data.teacher_id}")
    
    # Step 3: Hash password
    hashed_pwd = hash_password(register_data.password)
    
    # Step 4: Create teacher in admin's college
    new_teacher = Teacher(
        teacher_id=register_data.teacher_id,
        name=register_data.name,
        email=register_data.email,
        password_hash=hashed_pwd,
        college_id=current_user.college_id,
        role="teacher"
    )
    
    db.add(new_teacher)
    await db.commit()
    await db.refresh(new_teacher)
    
    # Step 5: Return success
    return MessageSchema(
        message=f"Teacher '{register_data.teacher_id}' registered successfully",
        status="success"
    )