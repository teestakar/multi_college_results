from sqlalchemy import Column, String, Integer, Float, DateTime, UUID, ForeignKey, ForeignKeyConstraint, Enum, Text, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

Base = declarative_base()

# ==================== COLLEGES TABLE ====================
class College(Base):
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    college_code = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    students = relationship("Student", back_populates="college")
    teachers = relationship("Teacher", back_populates="college")
    upload_batches = relationship("UploadBatch", back_populates="college")


# ==================== DEGREES TABLE ====================
class Degree(Base):
    __tablename__ = "degrees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

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
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

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
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    year = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    college = relationship("College", back_populates="students")
    degree_obj = relationship("Degree", back_populates="students")
    branch_obj = relationship("Branch", back_populates="students")
    marks = relationship(
        "Mark",
        back_populates="student",
        primaryjoin="and_(Student.roll_no==Mark.roll_no, Student.college_id==Mark.college_id)"
    )

    __table_args__ = (
        Index('idx_student_college_roll', 'college_id', 'roll_no'),
    )


# ==================== TEACHERS TABLE ====================
class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(String(50), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    role = Column(String(50), default="teacher")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    college = relationship("College", back_populates="teachers")
    marks = relationship("Mark", back_populates="uploaded_by_teacher")
    upload_batches = relationship("UploadBatch", back_populates="uploaded_by_teacher")


# ==================== MARKS TABLE ====================
class Mark(Base):
    __tablename__ = "marks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_no = Column(String(50), nullable=False)
    college_id = Column(UUID(as_uuid=True), nullable=False)
    semester = Column(Integer, nullable=False)
    subject_code = Column(String(50), nullable=False)
    subject_name = Column(String(255), nullable=False)
    grade = Column(String(5), nullable=False)
    points = Column(Float, nullable=False)
    credits = Column(Float, nullable=False)
    credit_points = Column(Float, nullable=False)
    uploaded_by = Column(String(50), ForeignKey("teachers.teacher_id"))
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    student = relationship(
        "Student",
        back_populates="marks",
        primaryjoin="and_(Mark.roll_no==Student.roll_no, Mark.college_id==Student.college_id)"
    )
    uploaded_by_teacher = relationship("Teacher", back_populates="marks")

    __table_args__ = (
        ForeignKeyConstraint(
            ["roll_no", "college_id"],
            ["students.roll_no", "students.college_id"]
        ),
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
    status = Column(String(50), default="pending")
    file_name = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    csv_content = Column(Text, nullable=True)
    marks_count = Column(Integer, default=0)

    college = relationship("College", back_populates="upload_batches")
    uploaded_by_teacher = relationship("Teacher", back_populates="upload_batches")


# ==================== SEMESTER GPA TABLE ====================
class SemesterGPA(Base):
    __tablename__ = "semester_gpa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_no = Column(String(50), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)

    sgpa = Column(Float, nullable=False)
    total_credits = Column(Float, nullable=False)
    total_credit_points = Column(Float, nullable=False)

    status = Column(String(50), nullable=False)
    backlog_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    needs_recalculation = Column(Boolean, default=False)

    student = relationship("Student", backref="semester_gpas")
    college = relationship("College", backref="semester_gpas")
    degree_obj = relationship("Degree", backref="semester_gpas")
    branch_obj = relationship("Branch", backref="semester_gpas")

    __table_args__ = (
        ForeignKeyConstraint(
            ["roll_no", "college_id"],
            ["students.roll_no", "students.college_id"]
        ),
        Index('idx_semgpa_student_sem', 'roll_no', 'college_id', 'semester'),
        Index('idx_semgpa_college_sem', 'college_id', 'semester'),
        Index('idx_semgpa_degree_sem', 'degree_id', 'semester'),
        Index('idx_semgpa_branch_sem', 'branch_id', 'semester'),
    )


# ==================== BACKGROUND TASKS TABLE ====================
class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(100), unique=True, nullable=False)
    task_type = Column(String(50), nullable=False)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    status = Column(String(20), default="pending")
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_bgtask_college_type_created', 'college_id', 'task_type', 'created_at'),
    )