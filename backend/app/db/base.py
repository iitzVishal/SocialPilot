# Import all the models here so that Alembic can detect them for autogenerate.
from app.db.base_class import Base
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus, CampaignStatus
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.social_account import SocialAccount
from app.models.team_invitation import TeamInvitation
from app.models.campaign import Campaign
from app.models.notification import Notification
from app.models.instagram_data import (
    InstagramMetricSnapshot,
    InstagramMedia,
    InstagramComment,
    MetaWebhookEvent,
)

__all__ = [
    "Base",
    "UserRole",
    "SocialPlatform",
    "SocialAccountStatus",
    "CampaignStatus",
    "User",
    "Team",
    "TeamMember",
    "SocialAccount",
    "TeamInvitation",
    "Campaign",
    "Notification",
    "InstagramMetricSnapshot",
    "InstagramMedia",
    "InstagramComment",
    "MetaWebhookEvent",
]
