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
                raise CSVParseError(
                details=f"Row {i}: Expected 8 columns, got {len(parts)}"
            )
            
            validated = CSVService._validate_row(parts, i)

            key = (
                validated["roll_no"],
                validated["semester"]
            )

            student_marks.setdefault(key, []).append({
                "subject_code": validated["subject_code"],
                "subject_name": validated["subject_name"],
                "grade": validated["grade"],
                "points": validated["points"],
                "credits": validated["credits"],
                "credit_points": validated["credit_points"],
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
                raise CSVParseError(
                details=f"Row {i}: Expected 8 columns, got {len(parts)}"
            )
            
            validated = CSVService._validate_row(parts, i)

            key = (
                validated["roll_no"],
                validated["semester"]
            )

            student_marks.setdefault(key, []).append({
                "subject_code": validated["subject_code"],
                "subject_name": validated["subject_name"],
                "grade": validated["grade"],
                "points": validated["points"],
                "credits": validated["credits"],
                "credit_points": validated["credit_points"],
            })
        
        return {
            "error": False,
            "student_marks": student_marks,
            "errors": errors,
            "skipped_rows": skipped_rows
        }
    
 
    @staticmethod
    async def process_and_insert_marks(student_marks, current_user, db):
        """
        Single function: Collect ALL marks from CSV, insert ALL at once (BULK)
        """
        
        inserted = 0
        updated = 0
        skipped = 0
        failed = 0
        
        marks_to_insert = []

        # ============================================================
        # NEW: Batch-fetch everything BEFORE the loops (fixes N+1)
        # ============================================================
        
        roll_nos = list({roll_no for (roll_no, _) in student_marks.keys()})

        # 1) Fetch ALL relevant students at once
        students_result = await db.execute(
            select(Student).where(
                (Student.college_id == current_user.college_id) &
                (Student.roll_no.in_(roll_nos))
            )
        )
        student_by_roll = {s.roll_no: s for s in students_result.scalars().all()}

        # 2) Fetch ALL existing marks for these students at once
        existing_marks_result = await db.execute(
            select(Mark).where(
                (Mark.college_id == current_user.college_id) &
                (Mark.roll_no.in_(roll_nos))
            )
        )
        # Key by (roll_no, semester, subject_code) — matches your uniqueness rule
        existing_mark_by_key = {
            (m.roll_no, m.semester, m.subject_code): m
            for m in existing_marks_result.scalars().all()
        }

        # 3) Fetch ALL existing SemesterGPA rows for these students at once
        sgpa_result = await db.execute(
            select(SemesterGPA).where(
                (SemesterGPA.college_id == current_user.college_id) &
                (SemesterGPA.roll_no.in_(roll_nos))
            )
        )
        sgpa_by_roll_sem = {
            (s.roll_no, s.semester): s
            for s in sgpa_result.scalars().all()
        }

        # ============================================================
        # Loops are now PURE PYTHON — no queries inside them
        # ============================================================

        for (roll_no, semester), marks in student_marks.items():

            student = student_by_roll.get(roll_no)
            if not student:
                failed += 1
                continue

            for m in marks:
                key = (roll_no, semester, m["subject_code"])
                existing_mark = existing_mark_by_key.get(key)

                if not existing_mark:
                    marks_to_insert.append({
                        "roll_no": roll_no,
                        "college_id": current_user.college_id,
                        "semester": semester,
                        "subject_code": m["subject_code"],
                        "subject_name": m["subject_name"],
                        "grade": m["grade"],
                        "points": m["points"],
                        "credits": m["credits"],
                        "credit_points": m["credit_points"],
                        "uploaded_by": current_user.teacher_id
                    })
                    inserted += 1

                    sgpa = sgpa_by_roll_sem.get((roll_no, semester))
                    if sgpa:
                        sgpa.needs_recalculation = True

                elif (
                    existing_mark.subject_name == m["subject_name"] and
                    existing_mark.grade == m["grade"] and
                    existing_mark.points == m["points"] and
                    existing_mark.credits == m["credits"] and
                    existing_mark.credit_points == m["credit_points"]
                ):
                    skipped += 1

                else:
                    existing_mark.subject_name = m["subject_name"]
                    existing_mark.grade = m["grade"]
                    existing_mark.points = m["points"]
                    existing_mark.credits = m["credits"]
                    existing_mark.credit_points = m["credit_points"]
                    updated += 1

                    sgpa = sgpa_by_roll_sem.get((roll_no, semester))
                    if sgpa:
                        sgpa.needs_recalculation = True

        if marks_to_insert:
            from sqlalchemy import insert
            await db.execute(insert(Mark).values(marks_to_insert))

        return {
            "inserted_marks": inserted,
            "updated_marks": updated,
            "skipped_marks": skipped,
            "failed_marks": failed
        }

    @staticmethod
    def _safe_int(value):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return None
        
    @staticmethod
    def _safe_float(value):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None
        
    @staticmethod
    def _validate_row(parts, row_number):
        """
        Validate one CSV row.
        Raises CSVParseError if any value is invalid.
        """

        # ---------- Roll Number ----------
        roll_no = parts[0].strip()

        if not roll_no:
            raise CSVParseError(
                details=f"Row {row_number}: Roll number cannot be empty"
            )

        if not roll_no.isdigit():
            raise CSVParseError(
                details=f"Row {row_number}: Roll number must contain only digits"
            )

        # ---------- Semester ----------
        semester = CSVService._safe_int(parts[1])

        if semester is None:
            raise CSVParseError(
                details=f"Row {row_number}: Semester must be an integer"
            )

        if semester < 1 or semester > 8:
            raise CSVParseError(
                details=f"Row {row_number}: Semester must be between 1 and 8"
            )

        # ---------- Subject Code ----------
        subject_code = parts[2].strip()

        if not subject_code:
            raise CSVParseError(
                details=f"Row {row_number}: Subject code cannot be empty"
            )

        # ---------- Subject Name ----------
        subject_name = parts[3].strip()

        if not subject_name:
            raise CSVParseError(
                details=f"Row {row_number}: Subject name cannot be empty"
            )

        # ---------- Grade ----------
        grade = parts[4].strip().upper()

        valid_grades = {
            "O",
            "E",
            "A",
            "B",
            "C",
            "F"
        }

        if grade not in valid_grades:
            raise CSVParseError(
                details=f"Row {row_number}: Invalid grade '{grade}'"
            )

        # ---------- Points ----------
        points = CSVService._safe_float(parts[5])

        if points is None:
            raise CSVParseError(
                details=f"Row {row_number}: Points must be numeric"
            )

        if points < 0 or points > 10:
            raise CSVParseError(
                details=f"Row {row_number}: Points must be between 0 and 10"
            )

        # ---------- Credits ----------
        credits = CSVService._safe_float(parts[6])

        if credits is None:
            raise CSVParseError(
                details=f"Row {row_number}: Credits must be numeric"
            )

        if credits <= 0:
            raise CSVParseError(
                details=f"Row {row_number}: Credits must be greater than 0"
            )

        # ---------- Credit Points ----------
        credit_points = CSVService._safe_float(parts[7])

        if credit_points is None:
            raise CSVParseError(
                details=f"Row {row_number}: Credit points must be numeric"
            )

        if credit_points < 0:
            raise CSVParseError(
                details=f"Row {row_number}: Credit points cannot be negative"
            )

        return {
            "roll_no": roll_no,
            "semester": semester,
            "subject_code": subject_code,
            "subject_name": subject_name,
            "grade": grade,
            "points": points,
            "credits": credits,
            "credit_points": credit_points
        }