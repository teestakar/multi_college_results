from sqlalchemy import Column, String, Integer, Float, DateTime, UUID, ForeignKey, Enum, Text, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime,timezone
import uuid

Base = declarative_base()

# ==================== COLLEGES TABLE ====================
class College(Base):
    __tablename__ = "colleges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)  # "Institute of Engineering & Management"
    college_code = Column(String(50), unique=True, nullable=False)  # "IEM"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    students = relationship("Student", back_populates="college")
    teachers = relationship("Teacher", back_populates="college")
   # marks = relationship("Mark", back_populates="college")
    upload_batches = relationship("UploadBatch", back_populates="college")


# ==================== DEGREES TABLE ====================
class Degree(Base):
    __tablename__ = "degrees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "B.Tech", "M.Tech", etc
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    college = relationship("College", backref="degrees")
    students = relationship("Student", back_populates="degree_obj")
    branches = relationship("Branch", back_populates="degree_obj")
    
    __table_args__ = (
        Index('idx_degree_college_name', 'college_id', 'name'),
    )


# ==================== BRANCHES TABLE ====================
class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "CSE", "ECE", "ME", etc
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    degree_obj = relationship("Degree", back_populates="branches")
    college = relationship("College", backref="branches")
    students = relationship("Student", back_populates="branch_obj")
    
    __table_args__ = (
        Index('idx_branch_degree_name', 'degree_id', 'name'),
        Index('idx_branch_college_name', 'college_id', 'name'),
    )


# ==================== STUDENTS TABLE ====================
class Student(Base):
    __tablename__ = "students"
    
    roll_no = Column(String(50), primary_key=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    # REMOVED: registration_no = Column(String(100))
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"), nullable=False)  # ← NEW
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)  # ← NEW
    year = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationships
    college = relationship("College", back_populates="students")
    degree_obj = relationship("Degree", back_populates="students")  # ← NEW
    branch_obj = relationship("Branch", back_populates="students")  # ← NEW
    marks = relationship(
        "Mark",
        back_populates="student",
        foreign_keys="[Mark.roll_no, Mark.college_id]",
        primaryjoin="and_(Student.roll_no==Mark.roll_no, Student.college_id==Mark.college_id)"
    )


# ==================== TEACHERS TABLE ====================
class Teacher(Base):
    __tablename__ = "teachers"
    
    teacher_id = Column(String(50), primary_key=True)  # "T001" - LOGIN ID
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    role = Column(String(50), default="teacher")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    college = relationship("College", back_populates="teachers")
    marks = relationship("Mark", back_populates="uploaded_by_teacher")
    upload_batches = relationship("UploadBatch", back_populates="uploaded_by_teacher")


# ==================== MARKS TABLE ====================
from sqlalchemy import and_

class Mark(Base):
    __tablename__ = "marks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_no = Column(String(50), ForeignKey("students.roll_no"), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("students.college_id"), nullable=False)
    semester = Column(Integer, nullable=False)
    subject_code = Column(String(50), nullable=False)
    subject_name = Column(String(255), nullable=False)
    grade = Column(String(5), nullable=False)
    points = Column(Float, nullable=False)
    credits = Column(Float, nullable=False)
    credit_points = Column(Float, nullable=False)
    uploaded_by = Column(String(50), ForeignKey("teachers.teacher_id"))
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    student = relationship(
        "Student",
        back_populates="marks",
        foreign_keys=[roll_no, college_id],
        primaryjoin="and_(Mark.roll_no==Student.roll_no, Mark.college_id==Student.college_id)"
    )
    uploaded_by_teacher = relationship("Teacher", back_populates="marks")

    __table_args__ = (
        Index('idx_mark_student_college', 'roll_no', 'college_id'),
        Index('idx_mark_college_semester', 'college_id', 'semester'),
        Index('idx_mark_college', 'college_id'),
    )

# ==================== UPLOAD BATCHES TABLE ====================
class UploadBatch(Base):
    __tablename__ = "upload_batches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    uploaded_by = Column(String(50), ForeignKey("teachers.teacher_id"), nullable=False)
   # semester = Column(Integer)  # Which semester was uploaded
   # year = Column(Integer)  # Which year
    status = Column(String(50), default="pending")  # "pending", "processing", "completed", "failed"
    file_name = Column(String(255))  # "CSE_Sem2_2024.xlsx"
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)  # If parsing failed, why?

    # NEW COLUMNS
    csv_content = Column(Text, nullable=True)    # ← ADD
    marks_count = Column(Integer, default=0)    # ← ADD
    
    # Relationships
    college = relationship("College", back_populates="upload_batches")
    uploaded_by_teacher = relationship("Teacher", back_populates="upload_batches")


    # ==================== SEMESTER GPA TABLE ====================
class SemesterGPA(Base):
    __tablename__ = "semester_gpa"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_no = Column(String(50), ForeignKey("students.roll_no"), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)  # Batch year
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    
    # SGPA & Credits
    sgpa = Column(Float, nullable=False)
    total_credits = Column(Float, nullable=False)
    total_credit_points = Column(Float, nullable=False)
    
    # Status
    status = Column(String(50), nullable=False)  # "pass", "pass_with_backlog", "fail"
    backlog_count = Column(Integer, default=0)  # How many subjects < 6.0
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    needs_recalculation = Column(Boolean, default=False)  # ← NEW FLAG
    
    # Relationships
    student = relationship("Student", backref="semester_gpas")
    college = relationship("College", backref="semester_gpas")
    degree_obj = relationship("Degree", backref="semester_gpas")
    branch_obj = relationship("Branch", backref="semester_gpas")
    
    __table_args__ = (
        Index('idx_semgpa_student_sem', 'roll_no', 'college_id', 'semester'),
        Index('idx_semgpa_college_sem', 'college_id', 'semester'),
        Index('idx_semgpa_degree_sem', 'degree_id', 'semester'),
        Index('idx_semgpa_branch_sem', 'branch_id', 'semester'),
    )


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(100), unique=True, nullable=False)  # Celery's task_id
    task_type = Column(String(50), nullable=False)  # "sgpa_calculation", "csv_approval", etc.
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, success, failed
    result_summary = Column(Text, nullable=True)   # JSON string of whatever the task returns
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_bgtask_college_type_created', 'college_id', 'task_type', 'created_at'),
    )