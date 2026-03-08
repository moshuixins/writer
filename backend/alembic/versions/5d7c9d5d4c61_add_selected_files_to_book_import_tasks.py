"""add selected_files to book import tasks

Revision ID: 5d7c9d5d4c61
Revises: a72f14d61789
Create Date: 2026-03-08 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '5d7c9d5d4c61'
down_revision = 'a72f14d61789'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('book_import_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('selected_files', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('book_import_tasks', schema=None) as batch_op:
        batch_op.drop_column('selected_files')
