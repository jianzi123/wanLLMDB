"""Add model registry tables

Revision ID: 005_add_model_registry
Revises: 004_add_run_logs
Create Date: 2024-11-16 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '005_add_model_registry'
down_revision = '004_add_run_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create model stage enum
    op.execute("""
        CREATE TYPE modelstage AS ENUM ('none', 'staging', 'production', 'archived')
    """)

    # Create registered_models table
    op.create_table(
        'registered_models',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', JSON, nullable=False, server_default='[]'),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # Create indexes and unique constraint for registered_models
    op.create_index('ix_registered_models_project_id', 'registered_models', ['project_id'])
    op.create_index('ix_registered_models_name', 'registered_models', ['name'])
    op.create_unique_constraint('uq_project_model_name', 'registered_models', ['project_id', 'name'])

    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stage', sa.Enum('none', 'staging', 'production', 'archived', name='modelstage'), nullable=False, server_default='none'),
        sa.Column('run_id', UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_version_id', UUID(as_uuid=True), nullable=True),
        sa.Column('metrics', JSON, nullable=False, server_default='{}'),
        sa.Column('tags', JSON, nullable=False, server_default='[]'),
        sa.Column('metadata', JSON, nullable=False, server_default='{}'),
        sa.Column('approved_by', UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['registered_models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id']),
        sa.ForeignKeyConstraint(['artifact_version_id'], ['artifact_versions.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
    )

    # Create indexes and unique constraint for model_versions
    op.create_index('ix_model_versions_model_id', 'model_versions', ['model_id'])
    op.create_index('ix_model_versions_stage', 'model_versions', ['stage'])
    op.create_index('ix_model_versions_run_id', 'model_versions', ['run_id'])
    op.create_unique_constraint('uq_model_version', 'model_versions', ['model_id', 'version'])

    # Create model_version_transitions table
    op.create_table(
        'model_version_transitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('model_version_id', UUID(as_uuid=True), nullable=False),
        sa.Column('from_stage', sa.Enum('none', 'staging', 'production', 'archived', name='modelstage'), nullable=False),
        sa.Column('to_stage', sa.Enum('none', 'staging', 'production', 'archived', name='modelstage'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('transitioned_by', UUID(as_uuid=True), nullable=False),
        sa.Column('transitioned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transitioned_by'], ['users.id']),
    )

    # Create index for model_version_transitions
    op.create_index('ix_model_version_transitions_model_version_id', 'model_version_transitions', ['model_version_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_model_version_transitions_model_version_id', table_name='model_version_transitions')
    op.drop_table('model_version_transitions')

    op.drop_index('ix_model_versions_run_id', table_name='model_versions')
    op.drop_index('ix_model_versions_stage', table_name='model_versions')
    op.drop_index('ix_model_versions_model_id', table_name='model_versions')
    op.drop_constraint('uq_model_version', 'model_versions', type_='unique')
    op.drop_table('model_versions')

    op.drop_index('ix_registered_models_name', table_name='registered_models')
    op.drop_index('ix_registered_models_project_id', table_name='registered_models')
    op.drop_constraint('uq_project_model_name', 'registered_models', type_='unique')
    op.drop_table('registered_models')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS modelstage')
