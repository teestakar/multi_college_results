from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.database import get_db
from database.models import Student, Mark
from database.schemas import ResultsResponseSchema, MarkResponseSchema
from auth.dependencies import get_current_user

router = APIRouter()


# ============================================================================
# GET STUDENT'S RESULTS
# ============================================================================

@router.get("/me")
async def get_my_results(
    semester: int = Query(None, description="Filter by semester (1, 2, 3, etc)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Starting position"),
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ResultsResponseSchema:
    """
    Get student's results/marks
    
    Query Parameters:
    - semester: Optional, filter by semester (1, 2, 3, etc)
    - limit: How many results per request (default 20, max 100)
    - offset: Starting position (default 0)
    
    Returns:
    - List of marks with pagination info
    - Uses indexes for fast queries
    - Only returns marks for the authenticated student's college
    
    Example:
    GET /api/results/me?semester=1&limit=20&offset=0
    
    Response:
    {
        "results": [
            {"id": "uuid", "semester": 1, "subject_code": "DSA", ...},
            {"id": "uuid", "semester": 1, "subject_code": "DBMS", ...}
        ],
        "total_count": 8,
        "limit": 20,
        "offset": 0,
        "semester": 1,
        "message": "Results fetched successfully"
    }
    """
    
    # Step 1: Build base query
    # Filter by current student AND college (multi-tenancy)
    query = select(Mark).where(
        (Mark.roll_no == current_user.roll_no) &
        (Mark.college_id == current_user.college_id)
    )
    
    # Step 2: Optionally filter by semester
    if semester is not None:
        query = query.where(Mark.semester == semester)
    
    # Step 3: Get total count (before pagination)
    # This tells frontend how many total results exist
    count_query = select(func.count(Mark.id)).where(
        (Mark.roll_no == current_user.roll_no) &
        (Mark.college_id == current_user.college_id)
    )
    if semester is not None:
        count_query = count_query.where(Mark.semester == semester)
    
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Step 4: Apply pagination
    # Fetch only 'limit' rows starting from 'offset'
    query = query.limit(limit).offset(offset)
    
    # Step 5: Execute query
    # Database uses our indexes (idx_mark_student_college) for FAST lookup
    result = await db.execute(query)
    marks = result.scalars().all()
    
    # Step 6: Convert ORM objects to Pydantic schemas
    mark_responses = [MarkResponseSchema.from_orm(mark) for mark in marks]
    
    # Step 7: Return complete response with pagination info
    return ResultsResponseSchema(
        results=mark_responses,
        total_count=total_count,
        limit=limit,
        offset=offset,
        semester=semester,
        message="Results fetched successfully"
    )