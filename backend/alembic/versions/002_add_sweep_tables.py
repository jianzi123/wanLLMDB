"""Add sweep tables for hyperparameter optimization

Revision ID: 002_add_sweep_tables
Revises: 001_artifact_tables
Create Date: 2024-11-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '002_add_sweep_tables'
down_revision = '001_artifact_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sweeps table
    op.create_table(
        'sweeps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('method', sa.Enum('random', 'grid', 'bayes', name='sweepmethod'), nullable=False, server_default='random'),
        sa.Column('metric_name', sa.String(255), nullable=False),
        sa.Column('metric_goal', sa.Enum('minimize', 'maximize', name='metricgoal'), nullable=False, server_default='maximize'),
        sa.Column('config', JSON, nullable=False),
        sa.Column('early_terminate', JSON, nullable=True),
        sa.Column('state', sa.Enum('pending', 'running', 'paused', 'finished', 'failed', 'canceled', name='sweepstate'), nullable=False, server_default='pending'),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('run_cap', sa.Integer(), nullable=True),
        sa.Column('best_run_id', UUID(as_uuid=True), nullable=True),
        sa.Column('best_value', sa.Float(), nullable=True),
        sa.Column('optuna_config', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['best_run_id'], ['runs.id'], ),
    )

    # Create indexes for sweeps
    op.create_index('ix_sweeps_name', 'sweeps', ['name'])
    op.create_index('ix_sweeps_project_id', 'sweeps', ['project_id'])
    op.create_index('ix_sweeps_state', 'sweeps', ['state'])

    # Create sweep_runs table
    op.create_table(
        'sweep_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('sweep_id', UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('trial_number', sa.Integer(), nullable=True),
        sa.Column('trial_state', sa.String(50), nullable=True),
        sa.Column('suggested_params', JSON, nullable=True),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('is_best', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['sweep_id'], ['sweeps.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
    )

    # Create indexes for sweep_runs
    op.create_index('ix_sweep_runs_sweep_id', 'sweep_runs', ['sweep_id'])
    op.create_index('ix_sweep_runs_run_id', 'sweep_runs', ['run_id'])

    # Add sweep_id column to runs table
    op.add_column('runs', sa.Column('sweep_id', UUID(as_uuid=True), nullable=True))
    op.create_index('ix_runs_sweep_id', 'runs', ['sweep_id'])
    op.create_foreign_key('fk_runs_sweep_id', 'runs', 'sweeps', ['sweep_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key and column from runs table
    op.drop_constraint('fk_runs_sweep_id', 'runs', type_='foreignkey')
    op.drop_index('ix_runs_sweep_id', table_name='runs')
    op.drop_column('runs', 'sweep_id')

    # Drop sweep_runs table
    op.drop_index('ix_sweep_runs_run_id', table_name='sweep_runs')
    op.drop_index('ix_sweep_runs_sweep_id', table_name='sweep_runs')
    op.drop_table('sweep_runs')

    # Drop sweeps table
    op.drop_index('ix_sweeps_state', table_name='sweeps')
    op.drop_index('ix_sweeps_project_id', table_name='sweeps')
    op.drop_index('ix_sweeps_name', table_name='sweeps')
    op.drop_table('sweeps')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS sweepmethod')
    op.execute('DROP TYPE IF EXISTS metricgoal')
    op.execute('DROP TYPE IF EXISTS sweepstate')
