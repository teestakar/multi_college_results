from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io

from database.database import get_db
from database.models import Student, Mark, Teacher
from database.schemas import ResultsResponseSchema, MarkResponseSchema, CSVUploadResponseSchema,MessageSchema
from auth.dependencies import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from database.models import Degree, Branch, SemesterGPA

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()



# ============================================================================
# GET DEGREES ENDPOINT
# ============================================================================

@router.get("/degrees")
async def get_degrees(
    current_user: Teacher = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """
    Get all degrees for current user's college
    
    Returns: [{id, name}, ...]
    """
    if not isinstance(current_user, Teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )
    
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
# GET BRANCHES ENDPOINT
# ============================================================================

@router.get("/branches")
async def get_branches(
    degree_id: str = Query(...),  # REQUIRED parameter
    current_user: Teacher = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """
    Get all branches for a specific degree
    
    Query Parameters:
    - degree_id: UUID of the degree
    
    Returns: [{id, name}, ...]
    """

    if not isinstance(current_user, Teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )
    
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
    current_user = Depends(get_current_user), 
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
    current_user: Teacher = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Production-grade CSV upload:
    - Safe parsing
    - Partial success
    - SGPA calculation
    - Duplicate prevention
    """

    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files allowed")

    contents = await file.read()
    csv_data = contents.decode("utf-8").strip().split("\n")

    if len(csv_data) < 2:
        raise HTTPException(400, "Empty CSV file")

   # Parse header (SAFE VERSION)
    header = csv_data[0].replace("\ufeff", "").strip().split(",")
    header = [h.strip().lower() for h in header]

    expected_headers = [
        "roll_no", "semester", "subject_code", "subject_name",
        "grade", "points", "credits", "credit_points"
    ]

    missing = set(expected_headers) - set(header)
    extra = set(header) - set(expected_headers)

    if missing or extra:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV header mismatch. Missing={missing}, Extra={extra}, Got={header}"
        )

    


    # ---------------- SAFE HELPERS ----------------
    def safe_int(v):
        try:
            return int(v.strip())
        except:
            return None

    def safe_float(v):
        try:
            return float(v.strip())
        except:
            return 0.0

    student_marks = {}

    errors = []
    skipped_rows = 0

    # ---------------- PARSE CSV ----------------
    for i, line in enumerate(csv_data[1:], start=2):
        if not line.strip():
            continue

        parts = line.split(",")

        if len(parts) != 8:
            errors.append(f"Row {i}: column mismatch")
            skipped_rows += 1
            continue

        roll_no = parts[0].strip()
        semester = safe_int(parts[1])

        if semester is None:
            errors.append(f"Row {i}: invalid semester")
            skipped_rows += 1
            continue

        key = (roll_no, semester)

        student_marks.setdefault(key, []).append({
            "subject_code": parts[2].strip(),
            "subject_name": parts[3].strip(),
            "grade": parts[4].strip(),
            "points": safe_float(parts[5]),
            "credits": safe_float(parts[6]),
            "credit_points": safe_float(parts[7]),
        })

    # ---------------- PROCESS STUDENTS ----------------
    success = 0
    failed = 0

    inserted_marks = 0
    inserted_sgpa = 0
    updated_marks = 0
    skipped_marks = 0

    for (roll_no, semester), marks in student_marks.items():
        try:
            # fetch student
            res = await db.execute(
                select(Student).where(
                    Student.roll_no == roll_no,
                    Student.college_id == current_user.college_id
                )
            )
            student = res.scalars().first()

            if not student:
                failed += 1
                errors.append(f"{roll_no}: student not found")
                continue

            

            # ---------------- SGPA CALCULATION ----------------
            total_credits = sum(m["credits"] for m in marks)
            total_cp = sum(m["credit_points"] for m in marks)

            if total_credits == 0:
                failed += 1
                errors.append(f"{roll_no}: zero credits")
                continue

            sgpa = total_cp / total_credits

            backlog = len([m for m in marks if m["points"] < 6.0])

            if backlog == 0:
                status = "pass"
            elif backlog <= 4:
                status = "pass_with_backlog"
            else:
                status = "fail"

            

            # ---------------- UPSERT SGPA ----------------

            existing_sgpa_result = await db.execute(
                select(SemesterGPA).where(
                    SemesterGPA.roll_no == roll_no,
                    SemesterGPA.semester == semester,
                    SemesterGPA.college_id == current_user.college_id
                )
            )

            existing_sgpa = existing_sgpa_result.scalars().first()

            if not existing_sgpa:

                db.add(
                    SemesterGPA(
                        roll_no=roll_no,
                        college_id=current_user.college_id,
                        semester=semester,
                        year=student.year,
                        degree_id=student.degree_id,
                        branch_id=student.branch_id,
                        sgpa=sgpa,
                        total_credits=total_credits,
                        total_credit_points=total_cp,
                        status=status,
                        backlog_count=backlog
                    )
                )

                inserted_sgpa += 1

            elif (
                existing_sgpa.sgpa == sgpa and
                existing_sgpa.total_credits == total_credits and
                existing_sgpa.total_credit_points == total_cp and
                existing_sgpa.status == status and
                existing_sgpa.backlog_count == backlog
            ):
                pass

            else:

                existing_sgpa.sgpa = sgpa
                existing_sgpa.total_credits = total_credits
                existing_sgpa.total_credit_points = total_cp
                existing_sgpa.status = status
                existing_sgpa.backlog_count = backlog
                existing_sgpa.year = student.year
                existing_sgpa.degree_id = student.degree_id
                existing_sgpa.branch_id = student.branch_id

                
            # ---------------- INSERT MARKS ----------------
            for m in marks:
                existing_mark_result = await db.execute(
                    select(Mark).where(
                        Mark.roll_no == roll_no,
                        Mark.semester == semester,
                        Mark.subject_code == m["subject_code"],
                        Mark.college_id == current_user.college_id
                    )
                )

                existing_mark = existing_mark_result.scalars().first()
                if not existing_mark:
                    # INSERT
                    db.add(Mark(

                    roll_no=roll_no,

                    college_id=current_user.college_id,

                    semester=semester,

                    subject_code=m["subject_code"],

                    subject_name=m["subject_name"],

                    grade=m["grade"],

                    points=m["points"],

                    credits=m["credits"],

                    credit_points=m["credit_points"],

                    uploaded_by=current_user.teacher_id

                    ))

                    inserted_marks += 1

                elif (
                    existing_mark.subject_name == m["subject_name"] and
                    existing_mark.grade == m["grade"] and
                    existing_mark.points == m["points"] and
                    existing_mark.credits == m["credits"] and
                    existing_mark.credit_points == m["credit_points"]
                ):
                    # SKIP
                    skipped_marks += 1

                else:
                    # UPDATE
                    existing_mark.subject_name = m["subject_name"]
                    existing_mark.grade = m["grade"]
                    existing_mark.points = m["points"]
                    existing_mark.credits = m["credits"]
                    existing_mark.credit_points = m["credit_points"]

                updated_marks += 1

            success += 1

        except Exception as e:
            failed += 1
            errors.append(f"{roll_no}: {str(e)}")

    # ---------------- COMMIT ----------------
    await db.commit()

    return {
        "status": "success",
        "message": "CSV processed",
        "students_processed": success,
        "students_failed": failed,

        "marks_inserted": inserted_marks,
        "marks_updated": updated_marks,
        "marks_skipped": skipped_marks,

        "sgpa_inserted": inserted_sgpa,

        "rows_skipped": skipped_rows,
        "errors": errors[:20]
    }

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
    current_user: Teacher = Depends(get_current_user),
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
    branch_text = f", {branch_id}" if branch_uuid else " (all branches)"
    
    if not semester_gpas:
        return {
            "degree_id": degree_id,
            "year": year,
            "semester": semester,
            "branch_id": branch_id,
            "total_students": 0,
            "pass_percentage": 0,
            "highest_sgpa": 0,
            "average_sgpa": 0,
            "lowest_sgpa": 0,
            "top_10_students": [],
            "sgpa_distribution": {},
            "subject_wise_failures": {},
            "message": f"No records found for Degree {degree_id}, Year {year}, Semester {semester}{branch_text}"
        }
    
    # Step 5: Calculate statistics
    total_students = len(semester_gpas)
    
    # Pass percentage (pass + pass_with_backlog)
    passed = len([s for s in semester_gpas if s.status != "fail"])
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