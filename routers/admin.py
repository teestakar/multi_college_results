# routers/admin.py

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database.database import get_db
from database.models import UploadBatch, Teacher, SemesterGPA, Mark,Student
from auth.permissions import require_admin
from auth.exceptions import ResourceNotFoundException, CSVProcessingError
from services.csv_service import CSVService
from services.cache_service import cache_service

router = APIRouter()


# ==================== ENDPOINT 1: List Pending Uploads ====================

@router.get("/uploads/pending")
async def list_pending_uploads(
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending uploads for this college
    
    Returns: List of pending uploads waiting for admin approval
    """
    
    try:
        # Query all pending uploads for this college
        result = await db.execute(
            select(UploadBatch).where(
                (UploadBatch.college_id == current_user.college_id) &
                (UploadBatch.status == "pending")
            ).order_by(UploadBatch.uploaded_at.desc())
        )
        
        uploads = result.scalars().all()
        
        # Format response
        pending_uploads = []
        for upload in uploads:
            # Get teacher name
            teacher_result = await db.execute(
                select(Teacher).where(Teacher.teacher_id == upload.uploaded_by)
            )
            teacher = teacher_result.scalars().first()
            
            pending_uploads.append({
                "upload_id": str(upload.id),
                "uploaded_by": upload.uploaded_by,
                "teacher_name": teacher.name if teacher else "Unknown",
                "marks_count": upload.marks_count,
                "file_name": upload.file_name,
                "uploaded_at": upload.uploaded_at.isoformat(),
                "status": upload.status
            })
        
        return {
            "status": "success",
            "count": len(pending_uploads),
            "uploads": pending_uploads,
            "message": f"{len(pending_uploads)} uploads pending approval"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending uploads: {str(e)}"
        )


# ==================== ENDPOINT 2: Download Upload CSV ====================

@router.get("/uploads/{upload_id}/download")
async def download_upload(
    upload_id: str,
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Download CSV file for review
    Admin can download and open in Excel/spreadsheet app
    """
    
    try:
        from uuid import UUID as PyUUID
        upload_uuid = PyUUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload_id format"
        )
    
    try:
        # Fetch upload with college isolation
        result = await db.execute(
            select(UploadBatch).where(
                (UploadBatch.id == upload_uuid) &
                (UploadBatch.college_id == current_user.college_id)
            )
        )
        
        upload = result.scalars().first()
        
        if not upload:
            raise ResourceNotFoundException("Upload")
        
        # Return as downloadable CSV file
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            iter([upload.csv_content.encode('utf-8')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={upload.file_name}"}
        )
    
    except ResourceNotFoundException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download upload: {str(e)}"
        )

# ==================== ENDPOINT 3: Approve Upload ====================

@router.post("/uploads/{upload_id}/approve")
async def approve_upload(
    upload_id: str,
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve upload and insert marks into system
    
    Flow:
    1. Fetch upload from upload_batches
    2. Parse CSV content
    3. Insert marks into marks table
    4. Update upload_batches status to "approved"
    5. Return result
    """
    
    try:
        from uuid import UUID as PyUUID
        upload_uuid = PyUUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload_id format"
        )
    
    try:
        # Step 1: Fetch upload
        result = await db.execute(
            select(UploadBatch).where(
                (UploadBatch.id == upload_uuid) &
                (UploadBatch.college_id == current_user.college_id)
            )
        )
        
        upload = result.scalars().first()
        
        if not upload:
            raise ResourceNotFoundException("Upload")
        
        if upload.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload status is {upload.status}, only 'pending' can be approved"
            )
        
        # Step 2: Parse CSV from stored content
        parsed_data = await CSVService._parse_csv_from_string(upload.csv_content)
        
        if parsed_data.get("error"):
            raise CSVProcessingError(details="CSV parsing failed")
        
        student_marks = parsed_data["student_marks"]
        
        # Step 3: Get the teacher who uploaded (for uploaded_by field)
        teacher_result = await db.execute(
            select(Teacher).where(Teacher.teacher_id == upload.uploaded_by)
        )
        uploader = teacher_result.scalars().first()
        
        if not uploader:
            raise ResourceNotFoundException("Teacher")
        
        # Step 4: Process marks (insert/update)
        mark_result = await CSVService.process_and_insert_marks(
            student_marks,
            uploader,  # Use the original teacher who uploaded
            db
        )
        
        # Step 5: Update upload_batches status
        upload.status = "approved"
        upload.completed_at = datetime.utcnow()
        await db.commit()
        
        cache_service.invalidate_pattern("stats_")
        
        # Step 6: Return result
        return {
            "status": "success",
            "upload_id": str(upload.id),
            "marks_inserted": mark_result["inserted_marks"],
            "marks_updated": mark_result["updated_marks"],
            "marks_skipped": mark_result["skipped_marks"],
           # "sgpa_inserted": mark_result["inserted_sgpa"],
            "message": f"Upload approved successfully. {mark_result['inserted_marks'] + mark_result['updated_marks']} marks processed"
        }
    
    except (ResourceNotFoundException, CSVProcessingError):
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"DEBUG: Approval error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve upload: {str(e)}"
        )
    


# ==================== ENDPOINT 4: Calculate SGPA ====================

@router.post("/calculate-sgpa")
async def calculate_sgpa(
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate SGPA for all students in all semesters that have marks
    
    No input needed - endpoint finds all marks and calculates SGPA for them
    
    Flow:
    1. Find all distinct (college_id, roll_no, semester) in marks table
    2. For each student-semester:
       - If SemesterGPA doesn't exist: CREATE new
       - If needs_recalculation=False: SKIP
       - If needs_recalculation=True: RECALCULATE and reset flag
    3. Return counts
    """
    
    try:
        print(f"DEBUG: Starting SGPA calculation for college={current_user.college_id}")
        
        # Step 1: Get all distinct (college_id, roll_no, semester) with marks
        result = await db.execute(
            select(
                Mark.college_id,
                Mark.roll_no,
                Mark.semester
            ).distinct().where(
                Mark.college_id == current_user.college_id
            )
        )
        
        student_semesters = result.all()
        print(f"DEBUG: Found {len(student_semesters)} student-semesters across all marks")
        
        if not student_semesters:
            return {
                "status": "success",
                "calculated": 0,
                "updated": 0,
                "message": "No marks found in system"
            }
        
        calculated = 0
        updated = 0
        
        for idx, (college_id, roll_no, sem) in enumerate(student_semesters):
            print(f"DEBUG: Processing {idx+1}/{len(student_semesters)}: roll_no={roll_no}, sem={sem}")
            
            try:
                # Get all marks for this student-semester
                marks_result = await db.execute(
                    select(Mark).where(
                        (Mark.roll_no == roll_no) &
                        (Mark.college_id == college_id) &
                        (Mark.semester == sem)
                    )
                )
                marks = marks_result.scalars().all()
                
                if not marks:
                    print(f"DEBUG: No marks found for {roll_no}")
                    continue
                
                print(f"DEBUG: Found {len(marks)} marks for {roll_no}, sem={sem}")
                
                # Calculate SGPA
                total_credits = sum(m.credits for m in marks)
                total_credit_points = sum(m.credit_points for m in marks)
                
                if total_credits == 0:
                    print(f"DEBUG: Zero credits for {roll_no}")
                    continue
                
                sgpa = total_credit_points / total_credits
                backlog_count = len([m for m in marks if m.points < 6.0])
                
                if backlog_count == 0:
                    status_val = "pass"
                elif backlog_count <= 4:
                    status_val = "pass_with_backlog"
                else:
                    status_val = "fail"
                
                print(f"DEBUG: Calculated SGPA={sgpa}, status={status_val}")
                
                # Get student info
                student_result = await db.execute(
                    select(Student).where(
                        (Student.roll_no == roll_no) &
                        (Student.college_id == college_id)
                    )
                )
                student = student_result.scalars().first()
                
                if not student:
                    print(f"DEBUG: Student not found for {roll_no}")
                    continue
                
                print(f"DEBUG: Student found: {student.name}")
                
                # Check if SemesterGPA exists
                sgpa_result = await db.execute(
                    select(SemesterGPA).where(
                        (SemesterGPA.roll_no == roll_no) &
                        (SemesterGPA.semester == sem) &
                        (SemesterGPA.college_id == college_id)
                    )
                )
                existing_sgpa = sgpa_result.scalars().first()
                
                if not existing_sgpa:
                    # Case 1: CREATE new SGPA
                    print(f"DEBUG: Creating new SGPA for {roll_no}")
                    new_sgpa = SemesterGPA(
                        roll_no=roll_no,
                        college_id=college_id,
                        semester=sem,
                        year=student.year,
                        degree_id=student.degree_id,
                        branch_id=student.branch_id,
                        sgpa=sgpa,
                        total_credits=total_credits,
                        total_credit_points=total_credit_points,
                        status=status_val,
                        backlog_count=backlog_count,
                        needs_recalculation=False
                    )
                    db.add(new_sgpa)
                    calculated += 1
                
                else:
                    # Case 2: Check flag
                    print(f"DEBUG: SGPA exists, needs_recalc={existing_sgpa.needs_recalculation}")
                    if not existing_sgpa.needs_recalculation:
                        print(f"DEBUG: Skipping {roll_no} (no changes needed)")
                        continue
                    
                    # RECALCULATE
                    print(f"DEBUG: Recalculating SGPA for {roll_no}")
                    existing_sgpa.sgpa = sgpa
                    existing_sgpa.total_credits = total_credits
                    existing_sgpa.total_credit_points = total_credit_points
                    existing_sgpa.status = status_val
                    existing_sgpa.backlog_count = backlog_count
                    existing_sgpa.needs_recalculation = False
                    updated += 1
            
            except Exception as inner_e:
                print(f"DEBUG: Error processing {roll_no}: {str(inner_e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        print(f"DEBUG: Committing... calculated={calculated}, updated={updated}")
        await db.commit()
        cache_service.invalidate_pattern("stats_")

        return {
            "status": "success",
            "calculated": calculated,
            "updated": updated,
            "message": f"SGPA calculation complete. {calculated} new, {updated} updated"
        }
    
    except Exception as e:
        await db.rollback()
        print(f"DEBUG: Error in calculate_sgpa: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate SGPA: {str(e)}"
        )


# ==================== ENDPOINT 4: Reject Upload ====================

@router.post("/uploads/{upload_id}/reject")
async def reject_upload(
    upload_id: str,
    body: dict,
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject an upload and mark it as rejected
    
    Admin can reject uploads if they find errors or issues
    
    Request body:
    {
        "reason": "Invalid marks format"
    }
    
    Flow:
    1. Fetch upload from upload_batches
    2. Check status is "pending"
    3. Set status to "rejected"
    4. Store rejection reason
    5. Update completed_at
    6. Return result
    """
    
    try:
        from uuid import UUID as PyUUID
        upload_uuid = PyUUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload_id format"
        )
    
    try:
        reason = body.get("reason", "No reason provided")
        
        # Step 1: Fetch upload
        result = await db.execute(
            select(UploadBatch).where(
                (UploadBatch.id == upload_uuid) &
                (UploadBatch.college_id == current_user.college_id)
            )
        )
        
        upload = result.scalars().first()
        
        if not upload:
            raise ResourceNotFoundException("Upload")
        
        # Step 2: Check status is pending
        if upload.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload status is {upload.status}, only 'pending' can be rejected"
            )
        
        # Step 3: Update status to rejected
        upload.status = "rejected"
        upload.error_message = reason
        upload.completed_at = datetime.utcnow()
        
        await db.commit()
        
        # Step 4: Return result
        return {
            "status": "success",
            "upload_id": str(upload.id),
            "action": "rejected",
            "reason": reason,
            "message": f"Upload rejected successfully. Reason: {reason}"
        }
    
    except ResourceNotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject upload: {str(e)}"
        )