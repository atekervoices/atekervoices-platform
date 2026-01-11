"""Add user demographic fields

Revision ID: 003_add_user_demographics
Revises: 002_add_contribution_limits
Create Date: 2026-01-11 03:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_user_demographics'
down_revision = '002_add_contribution_limits'
branch_labels = None
depends_on = None


def upgrade():
    # Add new demographic fields to user table
    op.add_column('user', sa.Column('region', sa.String(length=50), nullable=True))
    op.add_column('user', sa.Column('dialect', sa.String(length=50), nullable=True))


def downgrade():
    # Remove the fields if downgrading
    op.drop_column('user', 'dialect')
    op.drop_column('user', 'region')
