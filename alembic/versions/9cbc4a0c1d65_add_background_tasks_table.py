"""add background_tasks table

Revision ID: 9cbc4a0c1d65
Revises: 52079d48ee4d
Create Date: 2026-07-23 11:04:55.063773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cbc4a0c1d65'
down_revision: Union[str, Sequence[str], None] = '52079d48ee4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('background_tasks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('task_id', sa.String(length=100), nullable=False),
    sa.Column('task_type', sa.String(length=50), nullable=False),
    sa.Column('college_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('result_summary', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id')
    )
    op.create_index('idx_bgtask_college_type_created', 'background_tasks', ['college_id', 'task_type', 'created_at'], unique=False)
    op.alter_column('semester_gpa', 'needs_recalculation',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('upload_batches', 'marks_count',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('0'))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('upload_batches', 'marks_count',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))
    op.alter_column('semester_gpa', 'needs_recalculation',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.drop_index('idx_bgtask_college_type_created', table_name='background_tasks')
    op.drop_table('background_tasks')
    # ### end Alembic commands ###