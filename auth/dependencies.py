from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from database.database import get_db
from database.models import Student, Teacher
from auth.auth import decode_token
from auth.exceptions import InvalidTokenException

security = HTTPBearer()


async def get_current_user(
    credentials=Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except JWTError:
        raise InvalidTokenException()

    user_id: str = payload.get("user_id")
    college_id: str = payload.get("college_id")
    user_type: str = payload.get("user_type")

    if not user_id or not college_id or not user_type:
        raise InvalidTokenException()

    if user_type == "teacher":
        result = await db.execute(
            select(Teacher).where(
                (Teacher.teacher_id == user_id) &
                (Teacher.college_id == college_id)
            )
        )
        user = result.scalars().first()

    elif user_type == "student":
        result = await db.execute(
            select(Student).where(
                (Student.roll_no == user_id) &
                (Student.college_id == college_id)
            )
        )
        user = result.scalars().first()

    else:
        raise InvalidTokenException()

    if not user:
        raise InvalidTokenException()

    return user