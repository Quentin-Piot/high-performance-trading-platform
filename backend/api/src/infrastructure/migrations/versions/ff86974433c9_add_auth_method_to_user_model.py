"""Add auth_method to User model
Revision ID: ff86974433c9
Revises: 0004
Create Date: 2025-10-22 21:50:14.731020
"""
import sqlalchemy as sa
from alembic import op

revision = "ff86974433c9"
down_revision = "0004"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_method", sa.String(length=50), nullable=False, server_default="email"
        ),
    )
def downgrade() -> None:
    op.drop_column("users", "auth_method")
