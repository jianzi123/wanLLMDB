"""Add audit logs table for security and compliance tracking

Revision ID: 009
Revises: 008
Create Date: 2025-11-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audit_logs table with indexes."""

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('resource_name', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create single-column indexes
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_event_category', 'audit_logs', ['event_category'])
    op.create_index('ix_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_username', 'audit_logs', ['username'])
    op.create_index('ix_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Create composite indexes for common query patterns
    op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_category_created', 'audit_logs', ['event_category', 'created_at'])
    op.create_index('ix_audit_logs_severity_created', 'audit_logs', ['severity', 'created_at'])
    op.create_index('ix_audit_logs_resource_type_id', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_event_created', 'audit_logs', ['event_type', 'created_at'])


def downgrade() -> None:
    """Remove audit_logs table and indexes."""

    # Drop indexes
    op.drop_index('ix_audit_logs_event_created', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_type_id', 'audit_logs')
    op.drop_index('ix_audit_logs_severity_created', 'audit_logs')
    op.drop_index('ix_audit_logs_category_created', 'audit_logs')
    op.drop_index('ix_audit_logs_user_created', 'audit_logs')

    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_id', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_type', 'audit_logs')
    op.drop_index('ix_audit_logs_ip_address', 'audit_logs')
    op.drop_index('ix_audit_logs_username', 'audit_logs')
    op.drop_index('ix_audit_logs_user_id', 'audit_logs')
    op.drop_index('ix_audit_logs_severity', 'audit_logs')
    op.drop_index('ix_audit_logs_event_category', 'audit_logs')
    op.drop_index('ix_audit_logs_event_type', 'audit_logs')

    # Drop table
    op.drop_table('audit_logs')
