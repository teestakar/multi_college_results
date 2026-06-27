"""Add needs_recalculation flag to semester_gpa table

Revision ID: 52079d48ee4d
Revises: fbe0d4ad872b
Create Date: 2026-06-27 ...

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52079d48ee4d'
down_revision: Union[str, Sequence[str], None] = 'fbe0d4ad872b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add needs_recalculation column to semester_gpa table"""
    op.add_column('semester_gpa', sa.Column('needs_recalculation', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove needs_recalculation column"""
    op.drop_column('semester_gpa', 'needs_recalculation')