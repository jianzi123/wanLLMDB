"""Add artifact alias system

Revision ID: 006_add_artifact_aliases
Revises: 005_add_model_registry
Create Date: 2025-11-16 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '006_add_artifact_aliases'
down_revision = '005_add_model_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create artifact_aliases table
    op.create_table(
        'artifact_aliases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('artifact_id', UUID(as_uuid=True), nullable=False),
        sa.Column('version_id', UUID(as_uuid=True), nullable=False),
        sa.Column('alias', sa.String(100), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['artifact_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # Create indexes
    op.create_index('ix_artifact_aliases_artifact_id', 'artifact_aliases', ['artifact_id'])
    op.create_index('ix_artifact_aliases_version_id', 'artifact_aliases', ['version_id'])
    op.create_index('ix_artifact_aliases_alias', 'artifact_aliases', ['alias'])

    # Unique constraint: one artifact can only have one version with a specific alias
    op.create_unique_constraint('uq_artifact_alias', 'artifact_aliases', ['artifact_id', 'alias'])


def downgrade() -> None:
    # Drop constraints and indexes
    op.drop_constraint('uq_artifact_alias', 'artifact_aliases', type_='unique')
    op.drop_index('ix_artifact_aliases_alias', table_name='artifact_aliases')
    op.drop_index('ix_artifact_aliases_version_id', table_name='artifact_aliases')
    op.drop_index('ix_artifact_aliases_artifact_id', table_name='artifact_aliases')

    # Drop table
    op.drop_table('artifact_aliases')
