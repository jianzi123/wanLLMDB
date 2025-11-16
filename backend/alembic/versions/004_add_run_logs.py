"""Add run_logs table for log storage

Revision ID: 004_add_run_logs
Revises: 003_add_run_files
Create Date: 2024-11-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '004_add_run_logs'
down_revision = '003_add_run_files'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create run_logs table
    op.create_table(
        'run_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('level', sa.String(10), nullable=False, server_default='INFO'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('line_number', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    )

    # Create indexes for run_logs
    op.create_index('ix_run_logs_run_id', 'run_logs', ['run_id'])
    op.create_index('ix_run_logs_run_id_timestamp', 'run_logs', ['run_id', 'timestamp'])
    op.create_index('ix_run_logs_level', 'run_logs', ['level'])
    op.create_index('ix_run_logs_source', 'run_logs', ['source'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_run_logs_source', table_name='run_logs')
    op.drop_index('ix_run_logs_level', table_name='run_logs')
    op.drop_index('ix_run_logs_run_id_timestamp', table_name='run_logs')
    op.drop_index('ix_run_logs_run_id', table_name='run_logs')

    # Drop run_logs table
    op.drop_table('run_logs')
