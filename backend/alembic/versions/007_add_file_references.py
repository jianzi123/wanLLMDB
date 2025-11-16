"""Add external file reference support

Revision ID: 007_add_file_references
Revises: 006_add_artifact_aliases
Create Date: 2025-11-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_file_references'
down_revision = '006_add_artifact_aliases'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns for external file references
    op.add_column('artifact_files', sa.Column('is_reference', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('artifact_files', sa.Column('reference_uri', sa.String(1000), nullable=True))

    # Add index for reference lookups
    op.create_index('ix_artifact_files_is_reference', 'artifact_files', ['is_reference'])


def downgrade() -> None:
    # Drop index and columns
    op.drop_index('ix_artifact_files_is_reference', table_name='artifact_files')
    op.drop_column('artifact_files', 'reference_uri')
    op.drop_column('artifact_files', 'is_reference')
