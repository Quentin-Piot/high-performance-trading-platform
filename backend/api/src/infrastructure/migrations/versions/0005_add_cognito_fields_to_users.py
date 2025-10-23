"""Add cognito_sub and name fields to users table

Revision ID: 0005
Revises: ff86974433c9
Create Date: 2025-10-23 12:55:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = 'ff86974433c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cognito_sub and name fields to users table"""
    # Add cognito_sub column for Cognito user ID
    op.add_column('users', sa.Column('cognito_sub', sa.String(length=255), nullable=True))
    op.create_index('ix_users_cognito_sub', 'users', ['cognito_sub'], unique=True)
    
    # Add name column for user's display name
    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=True))
    
    # Make hashed_password nullable for Cognito users
    op.alter_column('users', 'hashed_password', nullable=True)


def downgrade() -> None:
    """Remove cognito_sub and name fields from users table"""
    # Make hashed_password non-nullable again
    op.alter_column('users', 'hashed_password', nullable=False)
    
    # Remove name column
    op.drop_column('users', 'name')
    
    # Remove cognito_sub column and its index
    op.drop_index('ix_users_cognito_sub', table_name='users')
    op.drop_column('users', 'cognito_sub')