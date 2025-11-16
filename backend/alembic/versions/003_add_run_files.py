"""Add run_files table for storing run-specific files

Revision ID: 003_add_run_files
Revises: 002_add_sweep_tables
Create Date: 2024-11-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '003_add_run_files'
down_revision = '002_add_sweep_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create run_files table
    op.create_table(
        'run_files',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('path', sa.String(512), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('storage_key', sa.String(512), nullable=False, unique=True),
        sa.Column('md5_hash', sa.String(32), nullable=True),
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    )

    # Create indexes for run_files
    op.create_index('ix_run_files_run_id', 'run_files', ['run_id'])
    op.create_index('ix_run_files_name', 'run_files', ['name'])
    op.create_index('ix_run_files_path', 'run_files', ['path'])
    op.create_index('ix_run_files_storage_key', 'run_files', ['storage_key'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_run_files_storage_key', table_name='run_files')
    op.drop_index('ix_run_files_path', table_name='run_files')
    op.drop_index('ix_run_files_name', table_name='run_files')
    op.drop_index('ix_run_files_run_id', table_name='run_files')

    # Drop run_files table
    op.drop_table('run_files')
