from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import SocialPlatform, SocialAccountStatus


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    platform = Column(Enum(SocialPlatform), nullable=False, index=True)
    account_identifier = Column(String(255), nullable=False)
    account_name = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    platform_permissions = Column(JSON, nullable=True)
    connection_status = Column(Enum(SocialAccountStatus), default=SocialAccountStatus.CONNECTED, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("platform", "account_identifier", "user_id", name="uq_platform_account_user"),
    )

    # Relationships
    user = relationship("User", back_populates="social_accounts")
    team = relationship("Team", back_populates="social_accounts")
