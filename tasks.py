# tasks.py
import asyncio
import json
from datetime import datetime,timezone
from celery_app import celery_app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from config import settings
from database.models import Mark, Student, SemesterGPA, BackgroundTask
from sqlalchemy import select
from database.models import UploadBatch, Teacher, BackgroundTask
from services.csv_service import CSVService

celery_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
CelerySessionLocal = async_sessionmaker(
    celery_engine,
    expire_on_commit=False,
    autoflush=False,
)


@celery_app.task(bind=True)
def calculate_sgpa_task(self, college_id):
    return asyncio.run(_calculate_sgpa_async(self.request.id, college_id))


async def _calculate_sgpa_async(task_id, college_id):
    async with CelerySessionLocal() as db:
        try:
            result = await db.execute(
                select(Mark.college_id, Mark.roll_no, Mark.semester)
                .distinct()
                .where(Mark.college_id == college_id)
            )
            student_semesters = result.all()

            if not student_semesters:
                await _mark_task_done(db, task_id, "success", {"calculated": 0, "updated": 0})
                return {"status": "success", "calculated": 0, "updated": 0}

            roll_nos = list({roll_no for (_, roll_no, _) in student_semesters})

            all_marks_result = await db.execute(
                select(Mark).where(
                    (Mark.college_id == college_id) & (Mark.roll_no.in_(roll_nos))
                )
            )
            marks_by_roll_sem = {}
            for m in all_marks_result.scalars().all():
                marks_by_roll_sem.setdefault((m.roll_no, m.semester), []).append(m)

            all_students_result = await db.execute(
                select(Student).where(
                    (Student.college_id == college_id) & (Student.roll_no.in_(roll_nos))
                )
            )
            student_by_roll = {s.roll_no: s for s in all_students_result.scalars().all()}

            all_sgpa_result = await db.execute(
                select(SemesterGPA).where(
                    (SemesterGPA.college_id == college_id) & (SemesterGPA.roll_no.in_(roll_nos))
                )
            )
            sgpa_by_roll_sem = {
                (s.roll_no, s.semester): s for s in all_sgpa_result.scalars().all()
            }

            calculated = 0
            updated = 0

            for (college_id_, roll_no, sem) in student_semesters:
                marks = marks_by_roll_sem.get((roll_no, sem), [])
                if not marks:
                    continue

                total_credits = sum(m.credits for m in marks)
                total_credit_points = sum(m.credit_points for m in marks)
                if total_credits == 0:
                    continue

                sgpa = total_credit_points / total_credits
                backlog_count = len([m for m in marks if m.points < 6.0])

                if backlog_count == 0:
                    status_val = "pass"
                elif backlog_count <= 4:
                    status_val = "pass_with_backlog"
                else:
                    status_val = "fail"

                student = student_by_roll.get(roll_no)
                if not student:
                    continue

                existing_sgpa = sgpa_by_roll_sem.get((roll_no, sem))

                if not existing_sgpa:
                    new_sgpa = SemesterGPA(
                        roll_no=roll_no,
                        college_id=college_id_,
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
                    if not existing_sgpa.needs_recalculation:
                        continue
                    existing_sgpa.sgpa = sgpa
                    existing_sgpa.total_credits = total_credits
                    existing_sgpa.total_credit_points = total_credit_points
                    existing_sgpa.status = status_val
                    existing_sgpa.backlog_count = backlog_count
                    existing_sgpa.needs_recalculation = False
                    updated += 1

            await db.commit()

            result_data = {"calculated": calculated, "updated": updated}
            await _mark_task_done(db, task_id, "success", result_data)

            return {"status": "success", **result_data}

        except Exception as e:
            await db.rollback()
            await _mark_task_done(db, task_id, "failed", None, error=str(e))
            raise


async def _mark_task_done(db, task_id, status, result_data, error=None):
    """Update the BackgroundTask row once the task finishes."""
    result = await db.execute(
        select(BackgroundTask).where(BackgroundTask.task_id == task_id)
    )
    task_record = result.scalars().first()

    if task_record:
        task_record.status = status
        task_record.completed_at = datetime.now(timezone.utc)
        if result_data is not None:
            task_record.result_summary = json.dumps(result_data)
        if error:
            task_record.error_message = error
        await db.commit()




@celery_app.task(bind=True)
def approve_upload_task(self, upload_id, college_id):
    """
    Celery entry point for CSV approval.
    self.request.id gives us the Celery task_id.
    """
    return asyncio.run(_approve_upload_async(self.request.id, upload_id, college_id))


async def _approve_upload_async(task_id, upload_id, college_id):
    """
    Actual async logic — same N+1-fixed pattern as calculate_sgpa.
    Opens CelerySessionLocal, does the work, updates BackgroundTask.
    """
    async with CelerySessionLocal() as db:
        try:
            # Step 1: Fetch the upload batch being approved
            result = await db.execute(
                select(UploadBatch).where(
                    (UploadBatch.id == upload_id) &
                    (UploadBatch.college_id == college_id)
                )
            )
            upload = result.scalars().first()

            if not upload:
                await _mark_task_done(db, task_id, "failed", None, error="Upload not found")
                return {"status": "failed", "error": "Upload not found"}

            if upload.status != "pending":
                await _mark_task_done(
                    db, task_id, "failed", None, 
                    error=f"Upload status is {upload.status}, not pending"
                )
                return {"status": "failed", "error": "Not pending"}

            # Step 2: Parse the CSV content
            parsed_data = await CSVService._parse_csv_from_string(upload.csv_content)
            student_marks = parsed_data["student_marks"]

            # Step 3: Get the teacher who uploaded this (for permission context)
            teacher_result = await db.execute(
                select(Teacher).where(Teacher.teacher_id == upload.uploaded_by)
            )
            uploader = teacher_result.scalars().first()

            if not uploader:
                await _mark_task_done(db, task_id, "failed", None, error="Uploader not found")
                return {"status": "failed", "error": "Uploader not found"}

            # Step 4: Process marks using the already-N+1-fixed service method
            mark_result = await CSVService.process_and_insert_marks(student_marks, uploader, db)

            # Step 5: Mark the upload as approved
            upload.status = "approved"
            upload.completed_at = datetime.now(timezone.utc)
            await db.commit()

            # Step 6: Invalidate stats cache (marks changed, cached stats are stale)
            from services.redis_cache_service import redis_cache_service
            redis_cache_service.invalidate_pattern("stats_")

            # Step 7: Record success in BackgroundTask
            result_data = {
                "inserted": mark_result["inserted_marks"],
                "updated": mark_result["updated_marks"],
                "skipped": mark_result["skipped_marks"],
                "failed": mark_result["failed_marks"],
            }
            await _mark_task_done(db, task_id, "success", result_data)

            return {"status": "success", **result_data}

        except Exception as e:
            await db.rollback()
            await _mark_task_done(db, task_id, "failed", None, error=str(e))
            raise