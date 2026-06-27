"""Remove semester and year from upload_batches - extract from CSV instead

Revision ID: fbe0d4ad872b
Revises: 80b679aaa006
Create Date: 2026-06-27 11:57:11.799119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbe0d4ad872b'
down_revision: Union[str, Sequence[str], None] = '80b679aaa006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove semester and year columns from upload_batches
    op.drop_column('upload_batches', 'semester')
    op.drop_column('upload_batches', 'year')
    
    # Make marks_count NOT NULL
    op.alter_column('upload_batches', 'marks_count',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse: Make marks_count nullable
    op.alter_column('upload_batches', 'marks_count',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('0'))
    
    # Re-add columns
    op.add_column('upload_batches', sa.Column('year', sa.Integer(), nullable=True))
    op.add_column('upload_batches', sa.Column('semester', sa.Integer(), nullable=True))