"""Add csv_content and marks_count to upload_batches

Revision ID: 80b679aaa006
Revises: 4d39bad1a693
Create Date: 2026-06-27 11:38:54.725035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80b679aaa006'
down_revision: Union[str, Sequence[str], None] = '4d39bad1a693'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('upload_batches', sa.Column('csv_content', sa.Text(), nullable=True))
    op.add_column('upload_batches', sa.Column('marks_count', sa.Integer(), nullable=False, server_default='0'))



def downgrade() -> None:
    op.drop_column('upload_batches', 'marks_count')
    op.drop_column('upload_batches', 'csv_content')