from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io
from services.csv_service import CSVService
from services.stats_service import StatsService
from database.database import get_db
from database.models import Student, Mark, Teacher
from database.schemas import ResultsResponseSchema, MarkResponseSchema, CSVUploadResponseSchema,MessageSchema
from auth.dependencies import get_current_user
from auth.permissions import require_teacher, require_admin, require_student,require_teacher_or_admin
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
    current_user: Teacher = Depends(require_teacher_or_admin),  # ← CHANGED: Use require_teacher!
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
    current_user: Teacher = Depends(require_teacher_or_admin),  # ← CHANGED: Use require_teacher!
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
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    from services.stats_service import StatsService
    
    return await StatsService.get_college_statistics(
        current_user.college_id, year, semester, degree_id, branch_id, db
    )


@router.get("/statistics/my-uploads")
@limiter.limit("100/hour")
async def get_my_uploads_statistics(
    request: Request,
    year: int = Query(...),
    semester: int = Query(...),
    degree_id: str = Query(...),
    branch_id: str = Query(None),
    current_user: Teacher = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    from services.stats_service import StatsService
    
    return await StatsService.get_teacher_upload_statistics(
        current_user.college_id, current_user.teacher_id, year, semester, degree_id, branch_id, db
    )