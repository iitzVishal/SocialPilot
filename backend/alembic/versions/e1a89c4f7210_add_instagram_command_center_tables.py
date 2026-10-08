"""add_instagram_command_center_tables

Revision ID: e1a89c4f7210
Revises: d94e1b8c4521
Create Date: 2026-10-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a89c4f7210'
down_revision: Union[str, None] = 'd94e1b8c4521'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new enum values to socialaccountstatus enum in Postgres
    op.execute("ALTER TYPE socialaccountstatus ADD VALUE IF NOT EXISTS 'SYNCING'")
    op.execute("ALTER TYPE socialaccountstatus ADD VALUE IF NOT EXISTS 'NEEDS_ATTENTION'")
    op.execute("ALTER TYPE socialaccountstatus ADD VALUE IF NOT EXISTS 'AUTHORIZATION_EXPIRED'")
    op.execute("ALTER TYPE socialaccountstatus ADD VALUE IF NOT EXISTS 'DISCONNECTED'")

    # 2. Add health & sync columns to social_accounts
    op.add_column('social_accounts', sa.Column('last_failed_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('social_accounts', sa.Column('sync_error', sa.Text(), nullable=True))
    op.add_column('social_accounts', sa.Column('sync_status', sa.String(length=50), server_default='idle', nullable=False))

    # 3. Create instagram_metric_snapshots
    op.create_table(
        'instagram_metric_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('follower_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('following_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('media_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('net_follower_growth', sa.Integer(), server_default='0', nullable=False),
        sa.Column('growth_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('impressions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reach', sa.Integer(), server_default='0', nullable=False),
        sa.Column('profile_views', sa.Integer(), server_default='0', nullable=False),
        sa.Column('website_clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'date', name='uq_ig_snapshot_account_date')
    )
    op.create_index(op.f('ix_instagram_metric_snapshots_id'), 'instagram_metric_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_instagram_metric_snapshots_account_id'), 'instagram_metric_snapshots', ['account_id'], unique=False)
    op.create_index(op.f('ix_instagram_metric_snapshots_team_id'), 'instagram_metric_snapshots', ['team_id'], unique=False)
    op.create_index(op.f('ix_instagram_metric_snapshots_date'), 'instagram_metric_snapshots', ['date'], unique=False)

    # 4. Create instagram_media
    op.create_table(
        'instagram_media',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('external_media_id', sa.String(length=255), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('media_type', sa.String(length=50), server_default='IMAGE', nullable=False),
        sa.Column('permalink', sa.String(length=1000), nullable=True),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('like_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('comments_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('views_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reach_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('shares_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('saved_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('engagement', sa.Integer(), server_default='0', nullable=False),
        sa.Column('performance_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('raw_insights', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'external_media_id', name='uq_ig_media_account_external_id')
    )
    op.create_index(op.f('ix_instagram_media_id'), 'instagram_media', ['id'], unique=False)
    op.create_index(op.f('ix_instagram_media_account_id'), 'instagram_media', ['account_id'], unique=False)
    op.create_index(op.f('ix_instagram_media_external_media_id'), 'instagram_media', ['external_media_id'], unique=False)
    op.create_index(op.f('ix_instagram_media_timestamp'), 'instagram_media', ['timestamp'], unique=False)

    # 5. Create instagram_comments
    op.create_table(
        'instagram_comments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('media_id', sa.Integer(), nullable=False),
        sa.Column('external_comment_id', sa.String(length=255), nullable=False),
        sa.Column('from_username', sa.String(length=255), nullable=True),
        sa.Column('from_user_id', sa.String(length=255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('like_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('parent_comment_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['media_id'], ['instagram_media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_comment_id', name='uq_ig_comment_external_id')
    )
    op.create_index(op.f('ix_instagram_comments_id'), 'instagram_comments', ['id'], unique=False)
    op.create_index(op.f('ix_instagram_comments_media_id'), 'instagram_comments', ['media_id'], unique=False)
    op.create_index(op.f('ix_instagram_comments_external_comment_id'), 'instagram_comments', ['external_comment_id'], unique=True)

    # 6. Create meta_webhook_events
    op.create_table(
        'meta_webhook_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('field', sa.String(length=100), nullable=False),
        sa.Column('account_identifier', sa.String(length=255), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', name='uq_meta_webhook_event_id')
    )
    op.create_index(op.f('ix_meta_webhook_events_id'), 'meta_webhook_events', ['id'], unique=False)
    op.create_index(op.f('ix_meta_webhook_events_event_id'), 'meta_webhook_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_meta_webhook_events_account_identifier'), 'meta_webhook_events', ['account_identifier'], unique=False)


def downgrade() -> None:
    op.drop_table('meta_webhook_events')
    op.drop_table('instagram_comments')
    op.drop_table('instagram_media')
    op.drop_table('instagram_metric_snapshots')
    op.drop_column('social_accounts', 'sync_status')
    op.drop_column('social_accounts', 'sync_error')
    op.drop_column('social_accounts', 'last_failed_sync_at')
