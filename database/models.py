from sqlalchemy import Column, String, Integer, Float, DateTime, UUID, ForeignKey, Enum, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# ==================== COLLEGES TABLE ====================
class College(Base):
    __tablename__ = "colleges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)  # "Institute of Engineering & Management"
    college_code = Column(String(50), unique=True, nullable=False)  # "IEM"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    students = relationship("Student", back_populates="college")
    teachers = relationship("Teacher", back_populates="college")
    marks = relationship("Mark", back_populates="college")
    upload_batches = relationship("UploadBatch", back_populates="college")


# ==================== STUDENTS TABLE ====================
class Student(Base):
    __tablename__ = "students"
    
    roll_no = Column(String(50), primary_key=True)  # "2024052002052" - LOGIN ID
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed
    name = Column(String(255), nullable=False)  # "TEESTA KAR"
    email = Column(String, nullable=True)
    registration_no = Column(String(100))  # "104202405200524 of 2024-25"
    degree = Column(String(50))  # "B.Tech"
    branch = Column(String(50))  # "CSE", "ECE"
    year = Column(Integer)  # 1, 2, 3, 4
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    college = relationship("College", back_populates="students")
    marks = relationship("Mark", back_populates="student")


# ==================== TEACHERS TABLE ====================
class Teacher(Base):
    __tablename__ = "teachers"
    
    teacher_id = Column(String(50), primary_key=True)  # "T001" - LOGIN ID
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    role = Column(String(50), default="teacher")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    college = relationship("College", back_populates="teachers")
    marks = relationship("Mark", back_populates="uploaded_by_teacher")
    upload_batches = relationship("UploadBatch", back_populates="uploaded_by_teacher")


# ==================== MARKS TABLE ====================
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
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="marks")
    college = relationship("College", back_populates="marks")
    uploaded_by_teacher = relationship("Teacher", back_populates="marks")

    __table_args__ = (
        Index('idx_mark_student', 'roll_no', 'college_id'),
        Index('idx_mark_college', 'college_id'),
    )

    

# ==================== UPLOAD BATCHES TABLE ====================
class UploadBatch(Base):
    __tablename__ = "upload_batches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=False)
    uploaded_by = Column(String(50), ForeignKey("teachers.teacher_id"), nullable=False)
    semester = Column(Integer)  # Which semester was uploaded
    year = Column(Integer)  # Which year
    status = Column(String(50), default="pending")  # "pending", "processing", "completed", "failed"
    file_name = Column(String(255))  # "CSE_Sem2_2024.xlsx"
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)  # If parsing failed, why?
    
    # Relationships
    college = relationship("College", back_populates="upload_batches")
    uploaded_by_teacher = relationship("Teacher", back_populates="upload_batches")