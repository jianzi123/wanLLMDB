"""add vdc and clusters

Revision ID: 012
Revises: 011
Create Date: 2025-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Create VDCs table
    op.create_table(
        'vdcs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_cpu_quota', sa.Float(), nullable=True),
        sa.Column('total_memory_quota', sa.Float(), nullable=True),
        sa.Column('total_gpu_quota', sa.Integer(), nullable=True),
        sa.Column('used_cpu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_memory', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_gpu', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_overcommit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('overcommit_ratio', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('default_scheduling_policy', sa.String(50), nullable=False, server_default='fifo'),
        sa.Column('cluster_selection_strategy', sa.String(50), nullable=False, server_default='load_balancing'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create Clusters table
    op.create_table(
        'clusters',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('vdc_id', UUID(as_uuid=True), sa.ForeignKey('vdcs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cluster_type', sa.Enum('kubernetes', 'slurm', name='clustertypeenum'), nullable=False, index=True),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('config', JSON, nullable=False, server_default='{}'),
        sa.Column('namespace', sa.String(255), nullable=True),
        sa.Column('total_cpu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_memory', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_gpu', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_cpu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_memory', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_gpu', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('healthy', 'degraded', 'unavailable', 'maintenance', name='clusterstatusenum'), nullable=False, server_default='healthy', index=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('labels', JSON, nullable=False, server_default='{}'),
        sa.Column('max_jobs_per_user', sa.Integer(), nullable=True),
        sa.Column('max_total_jobs', sa.Integer(), nullable=True),
        sa.Column('cost_per_cpu_hour', sa.Float(), nullable=True),
        sa.Column('cost_per_memory_gb_hour', sa.Float(), nullable=True),
        sa.Column('cost_per_gpu_hour', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create ProjectVDCQuotas table
    op.create_table(
        'project_vdc_quotas',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('vdc_id', UUID(as_uuid=True), sa.ForeignKey('vdcs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('cpu_quota', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('memory_quota', sa.Float(), nullable=False, server_default='500.0'),
        sa.Column('gpu_quota', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_concurrent_jobs', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('used_cpu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_memory', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('used_gpu', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_training_jobs', sa.Integer(), nullable=True),
        sa.Column('max_inference_jobs', sa.Integer(), nullable=True),
        sa.Column('max_workflow_jobs', sa.Integer(), nullable=True),
        sa.Column('current_training_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_inference_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_workflow_jobs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enforce_quota', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'vdc_id', name='uq_project_vdc'),
    )

    # Add VDC and Cluster fields to jobs table
    op.add_column('jobs', sa.Column('vdc_id', UUID(as_uuid=True), sa.ForeignKey('vdcs.id'), nullable=True, index=True))
    op.add_column('jobs', sa.Column('cluster_id', UUID(as_uuid=True), sa.ForeignKey('clusters.id'), nullable=True, index=True))
    op.add_column('jobs', sa.Column('preferred_cluster_ids', JSON, nullable=False, server_default='[]'))
    op.add_column('jobs', sa.Column('required_labels', JSON, nullable=False, server_default='{}'))


def downgrade():
    # Remove VDC columns from jobs table
    op.drop_column('jobs', 'required_labels')
    op.drop_column('jobs', 'preferred_cluster_ids')
    op.drop_column('jobs', 'cluster_id')
    op.drop_column('jobs', 'vdc_id')

    # Drop tables
    op.drop_table('project_vdc_quotas')
    op.drop_table('clusters')
    op.drop_table('vdcs')

    # Drop enums
    op.execute('DROP TYPE clusterstatusenum')
    op.execute('DROP TYPE clustertypeenum')
