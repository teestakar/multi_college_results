from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io

from database.database import get_db
from database.models import Student, Mark, Teacher
from database.schemas import ResultsResponseSchema, MarkResponseSchema, CSVUploadResponseSchema
from auth.dependencies import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


# ============================================================================
# GET STUDENT'S RESULTS
# ============================================================================

@router.get("/me")
@limiter.limit("100/hour")
async def get_my_results(
    request: Request, 
    semester: int = Query(None), 
    limit: int = Query(20, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: Student = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)) -> ResultsResponseSchema:
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
    """
    
    # Step 1: Build base query
    query = select(Mark).where(
        (Mark.roll_no == current_user.roll_no) &
        (Mark.college_id == current_user.college_id)
    )
    
    # Step 2: Optionally filter by semester
    if semester is not None:
        query = query.where(Mark.semester == semester)
    
    # Step 3: Get total count (before pagination)
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


# ============================================================================
# UPLOAD MARKS VIA CSV (Teacher/Admin only)
# ============================================================================

@router.post("/upload-csv")
@limiter.limit("5/hour")
async def upload_csv(
    request: Request, 
    file: UploadFile = File(...), 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)) -> CSVUploadResponseSchema:
    """
    Upload marks via CSV file (teacher/admin only)
    
    Input: CSV file with columns: roll_no, semester, subject_code, subject_name, grade, points, credits, credit_points
    Output: {message, inserted, updated, skipped, failed, errors}
    
    CSV Format:
    roll_no,semester,subject_code,subject_name,grade,points,credits,credit_points
    12024001,1,BSM301,Mathematics-III,O,10.0,3.0,30.0
    12024001,1,CS201,Data Structures,A,9.0,4.0,36.0
    
    Flow:
    1. Check: current_user is teacher or admin?
    2. Parse CSV
    3. For each row:
       - Validate data
       - Check if row exists
       - If exists and matches → skip
       - If exists and differs → update
       - If new → insert
    4. Return summary
    """
    
    # Step 1: Only teacher or admin can upload
    if not isinstance(current_user, Teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can upload CSV"
        )
    
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can upload CSV"
        )
    
    # Step 2: Validate file is CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    # Step 3: Read CSV file
    try:
        contents = await file.read()
        csv_reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
        rows = list(csv_reader)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading CSV: {str(e)}"
        )
    
    # Step 4: Initialize counters
    inserted = 0
    updated = 0
    skipped = 0
    failed = 0
    errors = []
    
    # Step 5: Process each row
    for row_num, row in enumerate(rows, start=2):  # start=2 (row 1 is header)
        try:
            # Validate required fields
            required_fields = ['roll_no', 'semester', 'subject_code', 'subject_name', 'grade', 'points', 'credits', 'credit_points']
            if not all(field in row for field in required_fields):
                errors.append({
                    "row": row_num,
                    "error": f"Missing required fields. Need: {', '.join(required_fields)}"
                })
                failed += 1
                continue
            
            # Validate and convert data types
            try:
                semester = int(row['semester'])
                points = float(row['points'])
                credits = float(row['credits'])
                credit_points = float(row['credit_points'])
            except ValueError as e:
                errors.append({
                    "row": row_num,
                    "roll_no": row.get('roll_no'),
                    "error": f"Invalid data type: {str(e)}"
                })
                failed += 1
                continue
            
            # Validate grade
            valid_grades = ['O', 'A', 'B', 'C', 'D', 'E']
            if row['grade'] not in valid_grades:
                errors.append({
                    "row": row_num,
                    "roll_no": row.get('roll_no'),
                    "error": f"Invalid grade '{row['grade']}'. Must be one of: {', '.join(valid_grades)}"
                })
                failed += 1
                continue
            
            # Validate student exists in college
            student_query = select(Student).where(
                (Student.roll_no == row['roll_no']) &
                (Student.college_id == current_user.college_id)
            )
            student_result = await db.execute(student_query)
            student = student_result.scalars().first()
            
            if not student:
                errors.append({
                    "row": row_num,
                    "roll_no": row.get('roll_no'),
                    "error": f"Student with roll_no '{row['roll_no']}' not found in your college"
                })
                failed += 1
                continue
            
            # Check if mark already exists
            existing_mark_query = select(Mark).where(
                (Mark.roll_no == row['roll_no']) &
                (Mark.semester == semester) &
                (Mark.subject_code == row['subject_code']) &
                (Mark.college_id == current_user.college_id)
            )
            existing_mark_result = await db.execute(existing_mark_query)
            existing_mark = existing_mark_result.scalars().first()
            
            if existing_mark:
                # Check if data matches exactly
                if (existing_mark.subject_name == row['subject_name'] and
                    existing_mark.grade == row['grade'] and
                    existing_mark.points == points and
                    existing_mark.credits == credits and
                    existing_mark.credit_points == credit_points):
                    # Exact match → skip
                    skipped += 1
                else:
                    # Data differs → update
                    existing_mark.subject_name = row['subject_name']
                    existing_mark.grade = row['grade']
                    existing_mark.points = points
                    existing_mark.credits = credits
                    existing_mark.credit_points = credit_points
                    existing_mark.uploaded_by = current_user.teacher_id
                    db.add(existing_mark)
                    updated += 1
            else:
                # New mark → insert
                new_mark = Mark(
                    roll_no=row['roll_no'],
                    semester=semester,
                    subject_code=row['subject_code'],
                    subject_name=row['subject_name'],
                    grade=row['grade'],
                    points=points,
                    credits=credits,
                    credit_points=credit_points,
                    uploaded_by=current_user.teacher_id,
                    college_id=current_user.college_id
                )
                db.add(new_mark)
                inserted += 1
        
        except Exception as e:
            errors.append({
                "row": row_num,
                "roll_no": row.get('roll_no', 'unknown'),
                "error": f"Unexpected error: {str(e)}"
            })
            failed += 1
            continue
    
    # Step 6: Commit all changes
    await db.commit()
    
    # Step 7: Return summary
    return CSVUploadResponseSchema(
        message=f"CSV upload processed: {inserted} inserted, {updated} updated, {skipped} skipped, {failed} failed",
        status="success" if failed == 0 else "partial",
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        failed=failed,
        errors=errors
    )


# ============================================================================
# STATISTICS ENDPOINT (Admin/Teacher view)
# ============================================================================

@router.get("/statistics")
@limiter.limit("100/hour")
async def get_statistics(
    request: Request, 
    semester: int = Query(None), 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)) -> dict:
    """
    Get result statistics for the college (admin/teacher only)
    
    Query Parameters:
    - semester: Optional, filter by semester (1, 2, 3, etc)
    
    Returns:
    {
        "total_marks": 150,
        "total_students": 50,
        "avg_points": 8.5,
        "pass_count": 140,
        "fail_count": 10,
        "by_semester": {
            "1": {"avg_points": 8.6, "pass_count": 75, "fail_count": 5},
            "2": {"avg_points": 8.4, "pass_count": 65, "fail_count": 5}
        }
    }
    """
    
    # Step 1: Only teacher or admin can view statistics
    if not isinstance(current_user, Teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can view statistics"
        )
    
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can view statistics"
        )
    
    # Step 2: Build base query (college-specific)
    base_query = select(Mark).where(
        Mark.college_id == current_user.college_id
    )
    
    # Optional: filter by semester
    if semester is not None:
        base_query = base_query.where(Mark.semester == semester)
    
    # Step 3: Execute query
    result = await db.execute(base_query)
    marks = result.scalars().all()
    
    # Step 4: Calculate statistics
    if not marks:
        # No marks in college yet
        return {
            "message": "No marks found",
            "total_marks": 0,
            "total_students": 0,
            "avg_points": 0.0,
            "pass_count": 0,
            "fail_count": 0,
            "by_semester": {}
        }
    
    # Count total marks
    total_marks = len(marks)
    
    # Count unique students
    unique_students = len(set([mark.roll_no for mark in marks]))
    
    # Calculate average points
    avg_points = sum([mark.points for mark in marks]) / total_marks
    
    # Count pass (>= 5.0 points) and fail (< 5.0 points)
    pass_count = len([m for m in marks if m.points >= 5.0])
    fail_count = len([m for m in marks if m.points < 5.0])
    
    # Group by semester
    by_semester = {}
    for mark in marks:
        sem = str(mark.semester)
        if sem not in by_semester:
            by_semester[sem] = {
                "marks": [],
                "pass": 0,
                "fail": 0
            }
        by_semester[sem]["marks"].append(mark.points)
        if mark.points >= 5.0:
            by_semester[sem]["pass"] += 1
        else:
            by_semester[sem]["fail"] += 1
    
    # Calculate semester stats
    semester_stats = {}
    for sem, data in by_semester.items():
        semester_stats[sem] = {
            "avg_points": sum(data["marks"]) / len(data["marks"]),
            "pass_count": data["pass"],
            "fail_count": data["fail"]
        }
    
    # Step 5: Return statistics
    return {
        "message": "Statistics retrieved successfully",
        "total_marks": total_marks,
        "total_students": unique_students,
        "avg_points": round(avg_points, 2),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "by_semester": semester_stats
    }