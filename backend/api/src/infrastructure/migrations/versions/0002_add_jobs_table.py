"""
Add jobs table for Monte Carlo queue system.

Revision ID: 0002_add_jobs_table
Revises: 0001_initial
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_jobs_table"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jobs table for Monte Carlo queue system
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifact_url", sa.String(500), nullable=True),
        sa.Column("dedup_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for performance
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_jobs_worker_id", "jobs", ["worker_id"])
    
    # Create unique constraint for deduplication
    op.create_unique_constraint("uq_job_dedup_key", "jobs", ["dedup_key"])


def downgrade() -> None:
    op.drop_constraint("uq_job_dedup_key", "jobs", type_="unique")
    op.drop_index("ix_jobs_worker_id", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")