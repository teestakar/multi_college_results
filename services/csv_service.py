# services/csv_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Student, Mark, SemesterGPA, Teacher, UploadBatch
from auth.exceptions import CSVParseError, CSVHeaderMismatchError, CSVProcessingError  # ← ADD THIS

class CSVService:
    
    @staticmethod
    async def process_upload(file, current_user: Teacher, db: AsyncSession):
        """
        NEW: Store CSV in staging (upload_batches), don't insert to marks yet
        """
        
        try:
            # Step 1: Parse CSV
            parsed_data = await CSVService._parse_csv(file)
            
            student_marks = parsed_data["student_marks"]
            csv_content = parsed_data["csv_content"]  # ← Get raw CSV content
            errors = parsed_data["errors"]
            
            # Step 2: Count total marks
            total_marks = sum(len(marks) for marks in student_marks.values())
            
            # Step 3: Create upload_batches entry (staging)
            upload_batch = UploadBatch(
                college_id=current_user.college_id,
                uploaded_by=current_user.teacher_id,
                csv_content=csv_content,        # ← Store CSV
                marks_count=total_marks,        # ← Store count
                status="pending",               # ← Waiting for approval
                file_name=file.filename
            )
            
            db.add(upload_batch)
            await db.commit()
            await db.refresh(upload_batch)
            
            # Step 4: Return upload_id and status
            return {
                "status": "pending",
                "upload_id": str(upload_batch.id),
                "marks_count": total_marks,
                "message": f"CSV uploaded successfully. {total_marks} marks waiting for admin approval",
                "errors": errors[:10]  # Show first 10 errors if any
            }
        
        except CSVParseError:
            raise
        except CSVHeaderMismatchError:
            raise
        except Exception as e:
            await db.rollback()
            raise CSVProcessingError(details=str(e))
        
    @staticmethod
    async def _parse_csv(file):
        """Parse and validate CSV file - raises exceptions"""
        
        # ← CHANGED: Raise exception instead of returning error dict
        if not file.filename.endswith(".csv"):
            raise CSVParseError(details="Only .csv files allowed")
        
        contents = await file.read()
        csv_text = contents.decode("utf-8").strip()  # ← Get raw text
        csv_data = contents.decode("utf-8").strip().split("\n")
        
        # ← CHANGED: Raise exception instead of returning error dict
        if len(csv_data) < 2:
            raise CSVParseError(details="File is empty")
        
        # Validate header
        header = csv_data[0].replace("\ufeff", "").strip().split(",")
        header = [h.strip().lower() for h in header]
        
        expected_headers = [
            "roll_no", "semester", "subject_code", "subject_name",
            "grade", "points", "credits", "credit_points"
        ]
        
        missing = set(expected_headers) - set(header)
        extra = set(header) - set(expected_headers)
        
        # ← CHANGED: Raise exception instead of returning error dict
        if missing or extra:
            raise CSVHeaderMismatchError(missing=missing, extra=extra)
        
        # Parse rows
        student_marks = {}
        errors = []
        skipped_rows = 0
        
        for i, line in enumerate(csv_data[1:], start=2):
            if not line.strip():
                continue
            
            parts = line.split(",")
            
            if len(parts) != 8:
                errors.append(f"Row {i}: column mismatch")
                skipped_rows += 1
                continue
            
            roll_no = parts[0].strip()
            semester = CSVService._safe_int(parts[1])
            
            if semester is None:
                errors.append(f"Row {i}: invalid semester")
                skipped_rows += 1
                continue
            
            key = (roll_no, semester)
            
            student_marks.setdefault(key, []).append({
                "subject_code": parts[2].strip(),
                "subject_name": parts[3].strip(),
                "grade": parts[4].strip(),
                "points": CSVService._safe_float(parts[5]),
                "credits": CSVService._safe_float(parts[6]),
                "credit_points": CSVService._safe_float(parts[7]),
            })
        
        # ← CHANGED: Return success dict, not error dict
        return {
            "error": False,
            "student_marks": student_marks,
            "csv_content": csv_text,  # ← ADD THIS
            "errors": errors,
            "skipped_rows": skipped_rows
        }
    

    @staticmethod
    async def _parse_csv_from_string(csv_text: str):
        """
        Parse CSV from string content (stored in DB)
        Same logic as _parse_csv but input is string instead of file
        
        Used by: Admin approval endpoint (reads csv_content from upload_batches)
        """
        
        csv_data = csv_text.strip().split("\n")
        
        # Validate not empty
        if len(csv_data) < 2:
            raise CSVParseError(details="File is empty")
        
        # Validate header
        header = csv_data[0].replace("\ufeff", "").strip().split(",")
        header = [h.strip().lower() for h in header]
        
        expected_headers = [
            "roll_no", "semester", "subject_code", "subject_name",
            "grade", "points", "credits", "credit_points"
        ]
        
        missing = set(expected_headers) - set(header)
        extra = set(header) - set(expected_headers)
        
        if missing or extra:
            raise CSVHeaderMismatchError(missing=missing, extra=extra)
        
        # Parse rows (exact same logic as _parse_csv)
        student_marks = {}
        errors = []
        skipped_rows = 0
        
        for i, line in enumerate(csv_data[1:], start=2):
            if not line.strip():
                continue
            
            parts = line.split(",")
            
            if len(parts) != 8:
                errors.append(f"Row {i}: column mismatch")
                skipped_rows += 1
                continue
            
            roll_no = parts[0].strip()
            semester = CSVService._safe_int(parts[1])
            
            if semester is None:
                errors.append(f"Row {i}: invalid semester")
                skipped_rows += 1
                continue
            
            key = (roll_no, semester)
            
            student_marks.setdefault(key, []).append({
                "subject_code": parts[2].strip(),
                "subject_name": parts[3].strip(),
                "grade": parts[4].strip(),
                "points": CSVService._safe_float(parts[5]),
                "credits": CSVService._safe_float(parts[6]),
                "credit_points": CSVService._safe_float(parts[7]),
            })
        
        return {
            "error": False,
            "student_marks": student_marks,
            "errors": errors,
            "skipped_rows": skipped_rows
        }
    
    @staticmethod
    async def _process_student_marks(student_marks, current_user, db):
        """
        Process all students and marks
        
        DO NOT calculate SGPA during upload/approval
        SGPA will be calculated separately when admin clicks button
        """
        
        success = 0
        failed = 0
        inserted_marks = 0
        updated_marks = 0
        skipped_marks = 0
        
        for (roll_no, semester), marks in student_marks.items():
            
            # Get student
            res = await db.execute(
                select(Student).where(
                    (Student.roll_no == roll_no) &
                    (Student.college_id == current_user.college_id)
                )
            )
            student = res.scalars().first()
            
            if not student:
                failed += 1
                continue
            
            # ❌ REMOVED: SGPA calculation
            # sgpa_result = await CSVService._calculate_and_save_sgpa(...)
            # We'll handle SGPA separately in Task 5
            
            # Process marks only
            mark_result = await CSVService._process_marks_for_student(
                roll_no, semester, marks, current_user, db
            )
            inserted_marks += mark_result["inserted"]
            updated_marks += mark_result["updated"]
            skipped_marks += mark_result["skipped"]
            
            success += 1
        
        return {
            "success": success,
            "failed": failed,
            "inserted_marks": inserted_marks,
            "updated_marks": updated_marks,
            "skipped_marks": skipped_marks,
            "inserted_sgpa": 0  # ← Always 0 now (no SGPA calculation)
        }
    
    @staticmethod
    async def _calculate_and_save_sgpa(roll_no, semester, marks, student, current_user, db):
        """Calculate SGPA and save to DB"""
        
        total_credits = sum(m["credits"] for m in marks)
        total_cp = sum(m["credit_points"] for m in marks)
        
        if total_credits == 0:
            return 0
        
        sgpa = total_cp / total_credits
        backlog = len([m for m in marks if m["points"] < 6.0])
        
        if backlog == 0:
            status = "pass"
        elif backlog <= 4:
            status = "pass_with_backlog"
        else:
            status = "fail"
        
        # Check if exists
        existing_sgpa_result = await db.execute(
            select(SemesterGPA).where(
                (SemesterGPA.roll_no == roll_no) &
                (SemesterGPA.semester == semester) &
                (SemesterGPA.college_id == current_user.college_id)
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
            return 1
        else:
            existing_sgpa.sgpa = sgpa
            existing_sgpa.total_credits = total_credits
            existing_sgpa.total_credit_points = total_cp
            existing_sgpa.status = status
            existing_sgpa.backlog_count = backlog
            return 0
    
    @staticmethod
    async def _process_marks_for_student(roll_no, semester, marks, current_user, db):
        """
        Process all marks for a student
        
        Also sets needs_recalculation flag if marks are updated
        """
        
        inserted = 0
        updated = 0
        skipped = 0
        
        for m in marks:
            # Check if mark already exists
            existing_mark_result = await db.execute(
                select(Mark).where(
                    (Mark.roll_no == roll_no) &
                    (Mark.semester == semester) &
                    (Mark.subject_code == m["subject_code"]) &
                    (Mark.college_id == current_user.college_id)
                )
            )
            existing_mark = existing_mark_result.scalars().first()
            
            if not existing_mark:
                # Case 1: NEW mark - just insert
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
                inserted += 1
                # Do nothing - SGPA will be created when admin clicks Calculate SGPA
            
            elif (
                existing_mark.subject_name == m["subject_name"] and
                existing_mark.grade == m["grade"] and
                existing_mark.points == m["points"] and
                existing_mark.credits == m["credits"] and
                existing_mark.credit_points == m["credit_points"]
            ):
                # Case 3: SAME mark - skip
                skipped += 1
                # Do nothing - leave flag unchanged
            
            else:
                # Case 2: UPDATED mark - update and set flag
                existing_mark.subject_name = m["subject_name"]
                existing_mark.grade = m["grade"]
                existing_mark.points = m["points"]
                existing_mark.credits = m["credits"]
                existing_mark.credit_points = m["credit_points"]
                updated += 1
                
                # ✅ Set flag for SGPA recalculation
                sgpa_result = await db.execute(
                    select(SemesterGPA).where(
                        (SemesterGPA.roll_no == roll_no) &
                        (SemesterGPA.semester == semester) &
                        (SemesterGPA.college_id == current_user.college_id)
                    )
                )
                sgpa = sgpa_result.scalars().first()
                
                if sgpa:
                    sgpa.needs_recalculation = True  # ✅ Mark as outdated
        
        return {"inserted": inserted, "updated": updated, "skipped": skipped}
    
    @staticmethod
    def _safe_int(v):
        try:
            return int(v.strip())
        except:
            return None
    
    @staticmethod
    def _safe_float(v):
        try:
            return float(v.strip())
        except:
            return 0.0