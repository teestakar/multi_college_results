"""Change student PK to composite (roll_no, college_id)

Revision ID: f511afa16785
Revises: 0f26944f4c85
Create Date: 2026-06-16 15:02:21.892464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f511afa16785'
down_revision: Union[str, Sequence[str], None] = '0f26944f4c85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - change student PK to composite (roll_no, college_id)"""
    
    # Step 1: Drop the old primary key constraint
    op.execute("ALTER TABLE students DROP CONSTRAINT students_pkey")
    
    # Step 2: Add new composite primary key
    op.execute("ALTER TABLE students ADD PRIMARY KEY (roll_no, college_id)")

def downgrade() -> None:
    """Downgrade schema - revert to single PK on roll_no"""
    
    # Step 1: Drop the composite primary key
    op.execute("ALTER TABLE students DROP CONSTRAINT students_pkey")
    
    # Step 2: Add back old primary key on roll_no only
    op.execute("ALTER TABLE students ADD PRIMARY KEY (roll_no)")