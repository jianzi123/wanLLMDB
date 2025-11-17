"""Add jobs table for cluster integration

Revision ID: 010
Revises: 009
Create Date: 2025-01-17 02:21:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create jobs table for K8s/Slurm cluster integration."""
    # Create job_type enum
    op.execute("""
        CREATE TYPE jobtypeenum AS ENUM ('training', 'inference', 'workflow')
    """)

    # Create job_executor enum
    op.execute("""
        CREATE TYPE jobexecutorenum AS ENUM ('kubernetes', 'slurm')
    """)

    # Create job_status enum
    op.execute("""
        CREATE TYPE jobstatusenum AS ENUM (
            'pending', 'queued', 'running', 'succeeded', 'failed', 'cancelled', 'timeout'
        )
    """)

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('job_type', sa.Enum('training', 'inference', 'workflow', name='jobtypeenum'), nullable=False),
        sa.Column('executor', sa.Enum('kubernetes', 'slurm', name='jobexecutorenum'), nullable=False),
        sa.Column('status', sa.Enum(
            'pending', 'queued', 'running', 'succeeded', 'failed', 'cancelled', 'timeout',
            name='jobstatusenum'
        ), nullable=False, server_default='pending'),

        # Relationships
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('runs.id'), nullable=True),

        # Job description
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', JSON, nullable=False, server_default='[]'),

        # Executor configuration
        sa.Column('executor_config', JSON, nullable=False),

        # Execution tracking
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('namespace', sa.String(255), nullable=True),
        sa.Column('exit_code', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('metrics', JSON, nullable=False, server_default='{}'),
        sa.Column('outputs', JSON, nullable=False, server_default='{}'),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_jobs_name', 'jobs', ['name'])
    op.create_index('ix_jobs_job_type', 'jobs', ['job_type'])
    op.create_index('ix_jobs_executor', 'jobs', ['executor'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_project_id', 'jobs', ['project_id'])
    op.create_index('ix_jobs_user_id', 'jobs', ['user_id'])
    op.create_index('ix_jobs_run_id', 'jobs', ['run_id'])
    op.create_index('ix_jobs_external_id', 'jobs', ['external_id'])
    op.create_index('ix_jobs_submitted_at', 'jobs', ['submitted_at'])

    # Composite indexes for common queries
    op.create_index('ix_jobs_project_status', 'jobs', ['project_id', 'status'])
    op.create_index('ix_jobs_user_status', 'jobs', ['user_id', 'status'])
    op.create_index('ix_jobs_type_status', 'jobs', ['job_type', 'status'])


def downgrade() -> None:
    """Drop jobs table."""
    # Drop indexes
    op.drop_index('ix_jobs_type_status', table_name='jobs')
    op.drop_index('ix_jobs_user_status', table_name='jobs')
    op.drop_index('ix_jobs_project_status', table_name='jobs')
    op.drop_index('ix_jobs_submitted_at', table_name='jobs')
    op.drop_index('ix_jobs_external_id', table_name='jobs')
    op.drop_index('ix_jobs_run_id', table_name='jobs')
    op.drop_index('ix_jobs_user_id', table_name='jobs')
    op.drop_index('ix_jobs_project_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_executor', table_name='jobs')
    op.drop_index('ix_jobs_job_type', table_name='jobs')
    op.drop_index('ix_jobs_name', table_name='jobs')

    # Drop table
    op.drop_table('jobs')

    # Drop enums
    op.execute('DROP TYPE jobstatusenum')
    op.execute('DROP TYPE jobexecutorenum')
    op.execute('DROP TYPE jobtypeenum')
