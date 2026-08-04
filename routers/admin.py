# routers/admin.py

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime,timezone
import time
from database.database import get_db
from database.models import UploadBatch, Teacher, SemesterGPA, Mark,Student
from auth.permissions import require_admin
from auth.exceptions import ResourceNotFoundException, CSVProcessingError, CSVParseError
from services.csv_service import CSVService
from services.cache_service import cache_service
from services.redis_cache_service import redis_cache_service
from tasks import calculate_sgpa_task  # ← ADD this import at the top of admin.py
from celery_app import celery_app  # ← ADD this import too
from database.models import BackgroundTask
import json
from tasks import approve_upload_task


router = APIRouter()


# ==================== ENDPOINT 1: List Pending Uploads ====================

@router.get("/uploads/pending")
async def list_pending_uploads(
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending uploads for this college
    """
    
    try:
        result = await db.execute(
            select(UploadBatch).where(
                (UploadBatch.college_id == current_user.college_id) &
                (UploadBatch.status == "pending")
            ).order_by(UploadBatch.uploaded_at.desc())
        )
        
        uploads = result.scalars().all()

        # ============================================================
        # NEW: Batch-fetch all relevant teachers in ONE query
        # ============================================================
        teacher_ids = list({upload.uploaded_by for upload in uploads})

        teachers_result = await db.execute(
            select(Teacher).where(Teacher.teacher_id.in_(teacher_ids))
        )
        teacher_by_id = {t.teacher_id: t for t in teachers_result.scalars().all()}

        # ============================================================
        # Loop is now pure Python — no queries inside it
        # ============================================================
        pending_uploads = []
        for upload in uploads:
            teacher = teacher_by_id.get(upload.uploaded_by)
            
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
    Enqueue CSV approval as a background task.
    Returns immediately with task_id instead of blocking.
    """
    from uuid import UUID as PyUUID
    
    try:
        upload_uuid = PyUUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload_id format")

    # Enqueue the task
    task = approve_upload_task.delay(str(upload_uuid), str(current_user.college_id))

    # Record it in BackgroundTask as pending
    task_record = BackgroundTask(
        task_id=task.id,
        task_type="csv_approval",
        college_id=current_user.college_id,
        status="pending"
    )
    db.add(task_record)
    await db.commit()

    return {
        "status": "queued",
        "task_id": task.id,
        "message": "CSV approval started in background"
    }    


# ==================== ENDPOINT 4: Calculate SGPA ====================


@router.post("/calculate-sgpa")
async def calculate_sgpa(
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    task = calculate_sgpa_task.delay(str(current_user.college_id))

    task_record = BackgroundTask(
        task_id=task.id,
        task_type="sgpa_calculation",
        college_id=current_user.college_id,
        status="pending"
    )
    db.add(task_record)
    await db.commit()

    return {
        "status": "queued",
        "task_id": task.id,
        "message": "SGPA calculation started in background"
    }




@router.get("/tasks/recent")
async def get_recent_tasks(
    task_type: str = Query(...),
    limit: int = Query(10, le=50),
    current_user: Teacher = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BackgroundTask)
        .where(
            (BackgroundTask.college_id == current_user.college_id) &
            (BackgroundTask.task_type == task_type)
        )
        .order_by(BackgroundTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()

    return [
        {
            "task_id": t.task_id,
            "status": t.status,
            "result": json.loads(t.result_summary) if t.result_summary else None,
            "error": t.error_message,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: Teacher = Depends(require_admin)
):
    """
    Poll this endpoint to check status of a background task.
    """
    task_result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task_result.status,  # PENDING, STARTED, SUCCESS, FAILURE
    }

    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)

    return response


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
        upload.completed_at = datetime.now(timezone.utc)
        
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