# services/stats_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import Mark, SemesterGPA
from fastapi import HTTPException, status


class StatsService:
    """Statistics service - keeps routes thin"""
    
    @staticmethod
    async def get_college_statistics(
        college_id,
        year: int,
        semester: int,
        degree_id,
        branch_id,
        db: AsyncSession
    ):
        """College-wide stats - moved from route"""
        
        try:
            from uuid import UUID as PyUUID
            degree_uuid = PyUUID(degree_id)
            branch_uuid = PyUUID(branch_id) if branch_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IDs")
        
        try:
            # Query SemesterGPA (exactly as before)
            query = select(SemesterGPA).where(
                (SemesterGPA.college_id == college_id) &
                (SemesterGPA.semester == semester) &
                (SemesterGPA.year == year) &
                (SemesterGPA.degree_id == degree_uuid)
            )
            
            if branch_uuid:
                query = query.where(SemesterGPA.branch_id == branch_uuid)
            
            result = await db.execute(query)
            semester_gpas = result.scalars().all()
            
            if not semester_gpas:
                raise HTTPException(status_code=404, detail="No records found")
            
            # Calculate statistics (all the same logic)
            total_students = len(semester_gpas)
            passed = sum(1 for s in semester_gpas if s.status in ("pass", "pass_with_backlog"))
            pass_percentage = (passed / total_students * 100) if total_students > 0 else 0
            
            sgpas = [s.sgpa for s in semester_gpas]
            highest_sgpa = max(sgpas)
            average_sgpa = sum(sgpas) / len(sgpas)
            lowest_sgpa = min(sgpas)
            
            # Top 10
            top_10 = sorted(semester_gpas, key=lambda x: x.sgpa, reverse=True)[:10]
            top_10_students = [
                {
                    "roll_no": s.roll_no,
                    "sgpa": round(s.sgpa, 2),
                    "status": s.status
                }
                for s in top_10
            ]
            
            # Distribution
            sgpa_distribution = {
                "9.0-10.0": len([s for s in semester_gpas if 9.0 <= s.sgpa <= 10.0]),
                "8.0-9.0": len([s for s in semester_gpas if 8.0 <= s.sgpa < 9.0]),
                "7.0-8.0": len([s for s in semester_gpas if 7.0 <= s.sgpa < 8.0]),
                "6.0-7.0": len([s for s in semester_gpas if 6.0 <= s.sgpa < 7.0]),
                "Below 6.0": len([s for s in semester_gpas if s.sgpa < 6.0])
            }
            
            # Subject-wise failures
            mark_query = select(Mark.subject_name, func.count(Mark.id)).where(
                (Mark.college_id == college_id) &
                (Mark.semester == semester) &
                (Mark.points < 6.0)
            ).group_by(Mark.subject_name)
            
            mark_result = await db.execute(mark_query)
            subject_wise_failures = {subject: count for subject, count in mark_result.all()}
            
            return {
                "degree_id": str(degree_id),
                "year": year,
                "semester": semester,
                "branch_id": str(branch_id) if branch_id else None,
                "total_students": total_students,
                "pass_percentage": round(pass_percentage, 2),
                "highest_sgpa": round(highest_sgpa, 2),
                "average_sgpa": round(average_sgpa, 2),
                "lowest_sgpa": round(lowest_sgpa, 2),
                "top_10_students": top_10_students,
                "sgpa_distribution": sgpa_distribution,
                "subject_wise_failures": subject_wise_failures,
                "message": f"Statistics for Degree {degree_id}, Year {year}, Semester {semester}"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    
    @staticmethod
    async def get_teacher_upload_statistics(
        college_id,
        teacher_id: str,
        year: int,
        semester: int,
        degree_id,
        branch_id,
        db: AsyncSession
    ):
        """Teacher upload stats - moved from route"""
        
        try:
            from uuid import UUID as PyUUID
            degree_uuid = PyUUID(degree_id)
            branch_uuid = PyUUID(branch_id) if branch_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IDs")
        
        try:
            # Step 1: Find marks I uploaded
            my_marks_result = await db.execute(
                select(Mark.roll_no).distinct().where(
                    (Mark.college_id == college_id) &
                    (Mark.semester == semester) &
                    (Mark.uploaded_by == teacher_id)
                )
            )
            my_student_rolls = [row[0] for row in my_marks_result.all()]
            
            if not my_student_rolls:
                return {
                    "total_students": 0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "pass_rate": 0,
                    "avg_sgpa": 0,
                    "with_backlog": 0,
                    "message": "No marks found for your uploads"
                }
            
            # Step 2: Get SGPA
            query = select(SemesterGPA).where(
                (SemesterGPA.college_id == college_id) &
                (SemesterGPA.semester == semester) &
                (SemesterGPA.roll_no.in_(my_student_rolls))
            )
            
            if branch_uuid:
                query = query.where(SemesterGPA.branch_id == branch_uuid)
            
            result = await db.execute(query)
            sgpas = result.scalars().all()
            
            if not sgpas:
                return {
                    "total_students": 0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "pass_rate": 0,
                    "avg_sgpa": 0,
                    "with_backlog": 0,
                    "message": "No SGPA data found for your uploads"
                }
            
            # Calculate
            total_students = len(sgpas)
            pass_count = len([s for s in sgpas if s.status == "pass"])
            fail_count = len([s for s in sgpas if s.status == "fail"])
            with_backlog = len([s for s in sgpas if s.backlog_count > 0])
            avg_sgpa = sum(s.sgpa for s in sgpas) / total_students
            pass_rate = (pass_count / total_students * 100) if total_students > 0 else 0
            
            return {
                "total_students": total_students,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "pass_rate": round(pass_rate, 2),
                "avg_sgpa": round(avg_sgpa, 2),
                "with_backlog": with_backlog,
                "year": year,
                "semester": semester,
                "degree_id": str(degree_id),
                "branch_id": str(branch_id) if branch_id else None,
                "message": f"Statistics for marks I uploaded - Semester {semester}, Year {year}"
            }
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")