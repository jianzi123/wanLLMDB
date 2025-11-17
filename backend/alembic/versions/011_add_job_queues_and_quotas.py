"""Add job queues and project quotas

Revision ID: 011
Revises: 010
Create Date: 2025-01-17 03:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create job_queues and project_quotas tables, update jobs table."""

    # Create job_queues table
    op.create_table(
        'job_queues',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),

        # Queue configuration
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_concurrent_jobs', sa.Integer, nullable=False, server_default='10'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),

        # Statistics
        sa.Column('total_jobs', sa.Integer, nullable=False, server_default='0'),
        sa.Column('running_jobs', sa.Integer, nullable=False, server_default='0'),
        sa.Column('pending_jobs', sa.Integer, nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for job_queues
    op.create_index('ix_job_queues_project_id', 'job_queues', ['project_id'])
    op.create_index('ix_job_queues_priority', 'job_queues', ['priority'])

    # Create project_quotas table
    op.create_table(
        'project_quotas',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True),

        # Quota limits
        sa.Column('cpu_quota', sa.Float, nullable=False, server_default='100.0'),
        sa.Column('memory_quota', sa.Float, nullable=False, server_default='500.0'),
        sa.Column('gpu_quota', sa.Integer, nullable=False, server_default='10'),
        sa.Column('max_concurrent_jobs', sa.Integer, nullable=False, server_default='50'),

        # Current usage
        sa.Column('used_cpu', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('used_memory', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('used_gpu', sa.Integer, nullable=False, server_default='0'),
        sa.Column('current_jobs', sa.Integer, nullable=False, server_default='0'),

        # Job limits per type
        sa.Column('max_training_jobs', sa.Integer, nullable=True),
        sa.Column('max_inference_jobs', sa.Integer, nullable=True),
        sa.Column('max_workflow_jobs', sa.Integer, nullable=True),

        # Current counts per type
        sa.Column('current_training_jobs', sa.Integer, nullable=False, server_default='0'),
        sa.Column('current_inference_jobs', sa.Integer, nullable=False, server_default='0'),
        sa.Column('current_workflow_jobs', sa.Integer, nullable=False, server_default='0'),

        # Quota enforcement
        sa.Column('enforce_quota', sa.Boolean, nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for project_quotas
    op.create_index('ix_project_quotas_project_id', 'project_quotas', ['project_id'])

    # Add new columns to jobs table
    op.add_column('jobs', sa.Column('queue_id', UUID(as_uuid=True), nullable=True))
    op.add_column('jobs', sa.Column('cpu_request', sa.Float, nullable=False, server_default='1.0'))
    op.add_column('jobs', sa.Column('memory_request', sa.Float, nullable=False, server_default='2.0'))
    op.add_column('jobs', sa.Column('gpu_request', sa.Integer, nullable=False, server_default='0'))
    op.add_column('jobs', sa.Column('queue_position', sa.Integer, nullable=True))
    op.add_column('jobs', sa.Column('enqueued_at', sa.DateTime(timezone=True), nullable=True))

    # Create foreign key for queue_id
    op.create_foreign_key('fk_jobs_queue_id', 'jobs', 'job_queues', ['queue_id'], ['id'])

    # Create indexes
    op.create_index('ix_jobs_queue_id', 'jobs', ['queue_id'])
    op.create_index('ix_jobs_queue_position', 'jobs', ['queue_position'])


def downgrade() -> None:
    """Drop job_queues and project_quotas tables, remove added columns from jobs."""

    # Drop indexes from jobs
    op.drop_index('ix_jobs_queue_position', table_name='jobs')
    op.drop_index('ix_jobs_queue_id', table_name='jobs')

    # Drop foreign key
    op.drop_constraint('fk_jobs_queue_id', 'jobs', type_='foreignkey')

    # Drop columns from jobs
    op.drop_column('jobs', 'enqueued_at')
    op.drop_column('jobs', 'queue_position')
    op.drop_column('jobs', 'gpu_request')
    op.drop_column('jobs', 'memory_request')
    op.drop_column('jobs', 'cpu_request')
    op.drop_column('jobs', 'queue_id')

    # Drop project_quotas table
    op.drop_index('ix_project_quotas_project_id', table_name='project_quotas')
    op.drop_table('project_quotas')

    # Drop job_queues table
    op.drop_index('ix_job_queues_priority', table_name='job_queues')
    op.drop_index('ix_job_queues_project_id', table_name='job_queues')
    op.drop_table('job_queues')
