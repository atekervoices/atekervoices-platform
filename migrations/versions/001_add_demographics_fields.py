"""Add age_group and gender fields to User model

Revision ID: 001
Revises: 
Create Date: 2026-01-07 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_add_demographics_fields'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add age_group column
    op.add_column('user', sa.Column('age_group', sa.String(length=20), nullable=True))
    
    # Add gender column  
    op.add_column('user', sa.Column('gender', sa.String(length=10), nullable=True))

def downgrade():
    # Remove gender column
    op.drop_column('user', 'gender')
    
    # Remove age_group column
    op.drop_column('user', 'age_group')
