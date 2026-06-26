from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io
from services.csv_service import CSVService
from database.database import get_db
from database.models import Student, Mark, Teacher
from database.schemas import ResultsResponseSchema, MarkResponseSchema, CSVUploadResponseSchema,MessageSchema
from auth.dependencies import get_current_user
from auth.permissions import require_teacher, require_admin, require_student
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from database.models import Degree, Branch, SemesterGPA

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()



# ============================================================================
# GET DEGREES ENDPOINT (UPDATED)
# ============================================================================

@router.get("/degrees")
async def get_degrees(
    current_user: Teacher = Depends(require_teacher),  # ← CHANGED: Use require_teacher!
    db: AsyncSession = Depends(get_db)):
    """
    Get all degrees for current user's college
    
    Returns: [{id, name}, ...]
    """
    # ← REMOVED: No need to check role here anymore!
    # if not isinstance(current_user, Teacher):
    #     raise UnauthorizedAccessException()
    
    try:
        result = await db.execute(
            select(Degree).where(
                Degree.college_id == current_user.college_id
            ).order_by(Degree.name)
        )
        degrees = result.scalars().all()
        
        return [
            {
                "id": str(degree.id),
                "name": degree.name
            }
            for degree in degrees
        ]
    except Exception as e:
        print(f"DEBUG: Error fetching degrees: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch degrees"
        )


# ============================================================================
# GET BRANCHES ENDPOINT (UPDATED)
# ============================================================================

@router.get("/branches")
async def get_branches(
    degree_id: str = Query(...),
    current_user: Teacher = Depends(require_teacher),  # ← CHANGED: Use require_teacher!
    db: AsyncSession = Depends(get_db)):
    """
    Get all branches for a specific degree
    
    Query Parameters:
    - degree_id: UUID of the degree
    
    Returns: [{id, name}, ...]
    """
    # ← REMOVED: No need to check role here anymore!
    # if not isinstance(current_user, Teacher):
    #     raise UnauthorizedAccessException()
    
    try:
        from uuid import UUID as PyUUID
        
        # Validate degree_id format
        try:
            degree_uuid = PyUUID(degree_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid degree_id format"
            )
        
        # Fetch branches for this degree in user's college
        result = await db.execute(
            select(Branch).where(
                (Branch.degree_id == degree_uuid) &
                (Branch.college_id == current_user.college_id)
            ).order_by(Branch.name)
        )
        branches = result.scalars().all()
        
        return [
            {
                "id": str(branch.id),
                "name": branch.name
            }
            for branch in branches
        ]
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error fetching branches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch branches"
        )

# ============================================================================
# GET STUDENT'S RESULTS
# ============================================================================

@router.get("/me")
async def get_my_results(
    semester: int = Query(None), 
    limit: int = Query(20, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user = Depends(require_student), 
    db: AsyncSession = Depends(get_db)):
    """
    Get student's results/marks with SGPA
    
    Query Parameters:
    - semester: Optional, filter by semester (1, 2, 3, etc)
    - limit: How many results per request (default 20, max 100)
    - offset: Starting position (default 0)
    
    Returns:
    - List of marks with pagination info
    - SGPA for each semester
    """
    
    # Step 1: Build base query for marks
    query = select(Mark).where(
        (Mark.roll_no == current_user.roll_no) &
        (Mark.college_id == current_user.college_id)
    )
    
    
    # Step 2: Optionally filter by semester
    if semester is not None:
        query = query.where(Mark.semester == semester)
    
    # Step 3: Get total count
    count_query = select(func.count(Mark.id)).where(
        (Mark.roll_no == current_user.roll_no) &
        (Mark.college_id == current_user.college_id)
    )
    if semester is not None:
        count_query = count_query.where(Mark.semester == semester)
    
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Step 4: Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Step 5: Execute query
    result = await db.execute(query)
    marks = result.scalars().all()
    
    # Step 6: Convert to response schema
    mark_responses = [MarkResponseSchema.from_orm(mark) for mark in marks]
    
    # Step 7: Fetch SGPA for this semester
    sgpa_data = None
    if semester is not None:
        sgpa_result = await db.execute(
            select(SemesterGPA).where(
                (SemesterGPA.roll_no == current_user.roll_no) &
                (SemesterGPA.college_id == current_user.college_id) &
                (SemesterGPA.semester == semester)
            )
        )
        sgpa = sgpa_result.scalars().first()
        if sgpa:
            sgpa_data = {
                "sgpa": round(sgpa.sgpa, 2),
                "status": sgpa.status,
                "backlog_count": sgpa.backlog_count
            }
    
    # Step 8: Return response
    return {
        "results": mark_responses,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "semester": semester,
        "sgpa": sgpa_data,
        "message": "Results fetched successfully"
    }

# ============================================================================
# UPLOAD MARKS VIA CSV (Teacher/Admin only)
# ============================================================================

@router.post("/upload-csv")
@limiter.limit("5/hour")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    current_user: Teacher = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    CSV upload endpoint - delegates to service layer
    """
    result = await CSVService.process_upload(file, current_user, db)
    return result    
    
# ============================================================================
# STATISTICS ENDPOINT (UPDATED)
# ============================================================================

@router.get("/statistics")
@limiter.limit("100/hour")
async def get_statistics(
    request: Request,
    degree_id: str = Query(...),
    year: int = Query(...),
    semester: int = Query(...),
    branch_id: str = Query(None),
    current_user: Teacher = Depends(require_teacher),  # ← CHANGED: Use require_teacher!
    db: AsyncSession = Depends(get_db)):
    """
    Get statistics for a specific degree, year, semester, and optional branch
    
    Query Parameters:
    - degree_id: UUID of degree - REQUIRED
    - year: Batch year (2022, 2023, etc) - REQUIRED
    - semester: Semester (1-8) - REQUIRED
    - branch_id: UUID of branch (optional, null = all branches for degree)
    
    Returns: SGPA-based statistics
    """
    
    # ← REMOVED: No need to check role here anymore!
    # if not isinstance(current_user, Teacher):
    #     raise UnauthorizedAccessException()
    
    # Step 1: Validate parameters
    if not degree_id or not year or not semester:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="degree_id, year, and semester are required"
        )
    # Step 2: Validate UUID format
    try:
        from uuid import UUID as PyUUID
        degree_uuid = PyUUID(degree_id)
        branch_uuid = PyUUID(branch_id) if branch_id else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid degree_id or branch_id format"
        )
    
    # Step 3: Query SemesterGPA table
    from sqlalchemy import and_, func
    
    query = select(SemesterGPA).where(
        (SemesterGPA.college_id == current_user.college_id) &
        (SemesterGPA.semester == semester) &
        (SemesterGPA.year == year) &
        (SemesterGPA.degree_id == degree_uuid)
    )
    
    if branch_uuid:
        query = query.where(SemesterGPA.branch_id == branch_uuid)


    
    result = await db.execute(query)
    semester_gpas = result.scalars().all()
    
    # Step 4: Handle no results
    branch_text = f", branch={branch_id}" if branch_id else " (all branches)"
    
    if not semester_gpas:
        raise HTTPException(
            status_code=404,
            detail="No records found for selected degree/year/semester/branch"
        )
    # Step 5: Calculate statistics
    total_students = len(semester_gpas)

    if total_students == 0:
        raise HTTPException(
            status_code=404,
            detail="No students found"
        )
    
    # Pass percentage (pass + pass_with_backlog)
    passed = sum(1 for s in semester_gpas if s.status in ("pass", "pass_with_backlog"))
    pass_percentage = (passed / total_students * 100) if total_students > 0 else 0
    
    # SGPA stats
    sgpas = [s.sgpa for s in semester_gpas]
    highest_sgpa = max(sgpas) if sgpas else 0
    average_sgpa = sum(sgpas) / len(sgpas) if sgpas else 0
    lowest_sgpa = min(sgpas) if sgpas else 0
    
    # Top 10 students
    top_10 = sorted(semester_gpas, key=lambda x: x.sgpa, reverse=True)[:10]
    top_10_students = []
    for sgpa in top_10:
        top_10_students.append({
            "roll_no": sgpa.roll_no,
            "sgpa": round(sgpa.sgpa, 2),
            "status": sgpa.status
        })
    
    # SGPA distribution (ranges)
    sgpa_distribution = {
        "9.0-10.0": len([s for s in semester_gpas if 9.0 <= s.sgpa <= 10.0]),
        "8.0-9.0": len([s for s in semester_gpas if 8.0 <= s.sgpa < 9.0]),
        "7.0-8.0": len([s for s in semester_gpas if 7.0 <= s.sgpa < 8.0]),
        "6.0-7.0": len([s for s in semester_gpas if 6.0 <= s.sgpa < 7.0]),
        "Below 6.0": len([s for s in semester_gpas if s.sgpa < 6.0])
    }
    
    # Subject-wise failure count (points < 6.0)
    mark_query = select(Mark.subject_name, func.count(Mark.id)).where(
        (Mark.college_id == current_user.college_id) &
        (Mark.semester == semester) &
        (Mark.points < 6.0)
    ).group_by(Mark.subject_name)
    
    mark_result = await db.execute(mark_query)
    subject_failures = mark_result.all()
    subject_wise_failures = {subject: count for subject, count in subject_failures}
    
    # Step 6: Return statistics
    return {
        "degree_id": degree_id,
        "year": year,
        "semester": semester,
        "branch_id": branch_id,
        "total_students": total_students,
        "pass_percentage": round(pass_percentage, 2),
        "highest_sgpa": round(highest_sgpa, 2),
        "average_sgpa": round(average_sgpa, 2),
        "lowest_sgpa": round(lowest_sgpa, 2),
        "top_10_students": top_10_students,
        "sgpa_distribution": sgpa_distribution,
        "subject_wise_failures": subject_wise_failures,
        "message": f"Statistics for Degree {degree_id}, Year {year}, Semester {semester}{branch_text}"
    }