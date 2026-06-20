"""Make degree_id and branch_id NOT NULL

Revision ID: 53ad2ba75879
Revises: 4d8ef3c9734d
Create Date: 2026-06-20 13:20:38.736271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53ad2ba75879'
down_revision: Union[str, Sequence[str], None] = '4d8ef3c9734d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('students', 'degree_id', existing_type=sa.UUID(), nullable=False)
    op.alter_column('students', 'branch_id', existing_type=sa.UUID(), nullable=False)

def downgrade() -> None:
    op.alter_column('students', 'degree_id', existing_type=sa.UUID(), nullable=True)
    op.alter_column('students', 'branch_id', existing_type=sa.UUID(), nullable=True)