import enum


class UserRole(str, enum.Enum):
    """Core user roles defined in the SocialPilot specification."""
    ADMINISTRATOR = "administrator"
    MARKETING_TEAM = "marketing_team"
    BUSINESS_USER = "business_user"
    CONTENT_CREATOR = "content_creator"


class SocialPlatform(str, enum.Enum):
    """Supported social media platforms defined in the SocialPilot specification."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"


class SocialAccountStatus(str, enum.Enum):
    """Connection status indicators for managed social accounts."""
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class PostStatus(str, enum.Enum):
    """Authoritative lifecycle states for multi-platform posts."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    PARTIALLY_PUBLISHED = "partially_published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublishResultStatus(str, enum.Enum):
    """Execution status for individual target social account dispatches."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_EXTERNAL_INTEGRATION = "pending_external_integration"
    UNCONFIGURED = "unconfigured"


class TeamInvitationStatus(str, enum.Enum):
    """Lifecycle states for team invitations."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CampaignStatus(str, enum.Enum):
    """Lifecycle states for marketing campaigns."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class NotificationType(str, enum.Enum):
    """Event types for in-app notifications."""
    TEAM_INVITATION = "team_invitation"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REJECTED = "invitation_rejected"
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    ROLE_CHANGED = "role_changed"
    POST_SUBMITTED = "post_submitted"
    POST_APPROVED = "post_approved"
    POST_REJECTED = "post_rejected"
    POST_PUBLISHED = "post_published"
    POST_FAILED = "post_failed"
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    CAMPAIGN_COMPLETED = "campaign_completed"
    SYSTEM = "system"

