"""add student college roll index

Revision ID: 011f8eacb26d
Revises: 792b31f07eb4
Create Date: 2026-08-06 00:22:10.896720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011f8eacb26d'
down_revision: Union[str, Sequence[str], None] = '792b31f07eb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_index(
        'idx_student_college_roll',
        'students',
        ['college_id', 'roll_no'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_index(
        'idx_student_college_roll',
        table_name='students'
    )