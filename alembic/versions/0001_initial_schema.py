"""Initial schema: users, devices, station_events, alerts.

Revision ID: 0001
Revises: 
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all four tables from scratch."""

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('station_id', sa.String(), nullable=False, unique=True),
        sa.Column('api_key_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_devices_station_id', 'devices', ['station_id'])

    op.create_table(
        'station_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('station_id', sa.String(), nullable=False),
        sa.Column('is_charging', sa.Boolean(), nullable=False),
        sa.Column('voltage', sa.Float(), nullable=True),
        sa.Column('amperage', sa.Float(), nullable=True),
        sa.Column('gps_lat', sa.Float(), nullable=True),
        sa.Column('gps_lng', sa.Float(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_station_events_station_id', 'station_events', ['station_id'])

    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('station_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.Enum('open', 'resolved', name='alertstatus'), nullable=False, server_default='open'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_alerts_station_id', 'alerts', ['station_id'])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table('alerts')
    op.drop_table('station_events')
    op.drop_table('devices')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS alertstatus')