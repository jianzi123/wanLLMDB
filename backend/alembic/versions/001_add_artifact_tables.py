"""Add artifact tables for file versioning

Revision ID: 001_artifact_tables
Revises:
Create Date: 2024-11-16 05:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '001_artifact_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('tags', JSON, nullable=True),
        sa.Column('version_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latest_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    )

    # Create indexes for artifacts
    op.create_index('ix_artifacts_name', 'artifacts', ['name'])
    op.create_index('ix_artifacts_type', 'artifacts', ['type'])
    op.create_index('ix_artifacts_project_id', 'artifacts', ['project_id'])

    # Create artifact_versions table
    op.create_table(
        'artifact_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('artifact_id', UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_size', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('digest', sa.String(64), nullable=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=True),
        sa.Column('is_finalized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    )

    # Create indexes for artifact_versions
    op.create_index('ix_artifact_versions_artifact_id', 'artifact_versions', ['artifact_id'])
    op.create_index('ix_artifact_versions_version', 'artifact_versions', ['version'])
    op.create_index('ix_artifact_versions_run_id', 'artifact_versions', ['run_id'])

    # Create artifact_files table
    op.create_table(
        'artifact_files',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('version_id', UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('md5_hash', sa.String(32), nullable=True),
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['artifact_versions.id'], ),
    )

    # Create indexes for artifact_files
    op.create_index('ix_artifact_files_version_id', 'artifact_files', ['version_id'])

    # Create artifact_downloads table
    op.create_table(
        'artifact_downloads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('version_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['artifact_versions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['file_id'], ['artifact_files.id'], ),
    )

    # Create indexes for artifact_downloads
    op.create_index('ix_artifact_downloads_version_id', 'artifact_downloads', ['version_id'])


def downgrade() -> None:
    # Drop tables in reverse order (to handle foreign key constraints)
    op.drop_index('ix_artifact_downloads_version_id', table_name='artifact_downloads')
    op.drop_table('artifact_downloads')

    op.drop_index('ix_artifact_files_version_id', table_name='artifact_files')
    op.drop_table('artifact_files')

    op.drop_index('ix_artifact_versions_run_id', table_name='artifact_versions')
    op.drop_index('ix_artifact_versions_version', table_name='artifact_versions')
    op.drop_index('ix_artifact_versions_artifact_id', table_name='artifact_versions')
    op.drop_table('artifact_versions')

    op.drop_index('ix_artifacts_project_id', table_name='artifacts')
    op.drop_index('ix_artifacts_type', table_name='artifacts')
    op.drop_index('ix_artifacts_name', table_name='artifacts')
    op.drop_table('artifacts')
