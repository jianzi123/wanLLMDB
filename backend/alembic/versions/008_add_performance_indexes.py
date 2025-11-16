"""Add performance indexes

Revision ID: 008
Revises: 007
Create Date: 2025-11-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add composite indexes for common queries to improve performance."""

    # Indexes for runs table - for project stats queries
    op.create_index(
        'ix_runs_project_created',
        'runs',
        ['project_id', 'created_at'],
        unique=False
    )

    # Indexes for artifacts table - for artifact queries by project and type
    op.create_index(
        'ix_artifacts_project_type',
        'artifacts',
        ['project_id', 'type'],
        unique=False
    )

    op.create_index(
        'ix_artifacts_name_type',
        'artifacts',
        ['name', 'type'],
        unique=False
    )

    # Indexes for artifact_versions table - for version queries
    op.create_index(
        'ix_artifact_versions_artifact_created',
        'artifact_versions',
        ['artifact_id', 'created_at'],
        unique=False
    )

    # Indexes for artifact_files table - for file queries
    op.create_index(
        'ix_artifact_files_version_path',
        'artifact_files',
        ['version_id', 'path'],
        unique=False
    )

    # Indexes for projects table - for search queries
    op.create_index(
        'ix_projects_visibility_created',
        'projects',
        ['visibility', 'created_at'],
        unique=False
    )

    op.create_index(
        'ix_projects_created_by',
        'projects',
        ['created_by'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""

    op.drop_index('ix_projects_created_by', table_name='projects')
    op.drop_index('ix_projects_visibility_created', table_name='projects')
    op.drop_index('ix_artifact_files_version_path', table_name='artifact_files')
    op.drop_index('ix_artifact_versions_artifact_created', table_name='artifact_versions')
    op.drop_index('ix_artifacts_name_type', table_name='artifacts')
    op.drop_index('ix_artifacts_project_type', table_name='artifacts')
    op.drop_index('ix_runs_project_created', table_name='runs')
