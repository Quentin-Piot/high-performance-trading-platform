"""Add job timing fields for duration tracking

Revision ID: 0003
Revises: 0002
Create Date: 2024-12-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add started_at and completed_at fields to jobs table"""
    # Add timing fields for job duration tracking
    op.add_column('jobs', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove started_at and completed_at fields from jobs table"""
    op.drop_column('jobs', 'completed_at')
    op.drop_column('jobs', 'started_at')