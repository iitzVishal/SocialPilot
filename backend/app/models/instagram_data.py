from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Date, DateTime, ForeignKey, JSON, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class InstagramMetricSnapshot(Base):
    __tablename__ = "instagram_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    follower_count = Column(Integer, default=0, nullable=False)
    following_count = Column(Integer, default=0, nullable=False)
    media_count = Column(Integer, default=0, nullable=False)
    net_follower_growth = Column(Integer, default=0, nullable=False)
    growth_rate = Column(Float, default=0.0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    reach = Column(Integer, default=0, nullable=False)
    profile_views = Column(Integer, default=0, nullable=False)
    website_clicks = Column(Integer, default=0, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_ig_snapshot_account_date"),
    )

    # Relationships
    social_account = relationship("SocialAccount", back_populates="metric_snapshots")
    team = relationship("Team")


class InstagramMedia(Base):
    __tablename__ = "instagram_media"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_media_id = Column(String(255), nullable=False, index=True)
    caption = Column(Text, nullable=True)
    media_type = Column(String(50), default="IMAGE", nullable=False)
    permalink = Column(String(1000), nullable=True)
    media_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    like_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    reach_count = Column(Integer, default=0, nullable=False)
    shares_count = Column(Integer, default=0, nullable=False)
    saved_count = Column(Integer, default=0, nullable=False)
    engagement = Column(Integer, default=0, nullable=False)
    performance_score = Column(Float, default=0.0, nullable=False)
    raw_insights = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "external_media_id", name="uq_ig_media_account_external_id"),
    )

    # Relationships
    social_account = relationship("SocialAccount", back_populates="media_items")
    comments = relationship("InstagramComment", back_populates="media", cascade="all, delete-orphan")


class InstagramComment(Base):
    __tablename__ = "instagram_comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey("instagram_media.id", ondelete="CASCADE"), nullable=False, index=True)
    external_comment_id = Column(String(255), nullable=False, unique=True, index=True)
    from_username = Column(String(255), nullable=True)
    from_user_id = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    like_count = Column(Integer, default=0, nullable=False)
    parent_comment_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media = relationship("InstagramMedia", back_populates="comments")


class MetaWebhookEvent(Base):
    __tablename__ = "meta_webhook_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    field = Column(String(100), nullable=False)
    account_identifier = Column(String(255), nullable=True, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
