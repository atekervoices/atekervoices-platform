"""Add contribution limits and session tracking

Revision ID: 002_add_contribution_limits
Revises: 001_add_demographics_fields
Create Date: 2026-01-10 17:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_contribution_limits'
down_revision = '001_add_demographics_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add session_id column to recordings table
    op.add_column('recording', sa.Column('session_id', sa.String(length=36), nullable=False))
    
    # Create unique constraint for one recording per sentence per user
    op.create_unique_constraint('unique_user_prompt', 'recording', ['user_id', 'language', 'prompt_group', 'prompt_id'])
    
    # Create recording_sessions table
    op.create_table('recording_session',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('recordings_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for session lookups
    op.create_index('ix_recording_session_user_language', 'recording_session', ['user_id', 'language'])


def downgrade():
    # Drop indexes and tables
    op.drop_index('ix_recording_session_user_language', table_name='recording_session')
    op.drop_table('recording_session')
    
    # Drop unique constraint
    op.drop_constraint('unique_user_prompt', 'recording', type_='unique')
    
    # Drop session_id column
    op.drop_column('recording', 'session_id')
