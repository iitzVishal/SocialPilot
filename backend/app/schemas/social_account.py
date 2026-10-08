from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import SocialPlatform, SocialAccountStatus


class SocialAccountBase(BaseModel):
    platform: SocialPlatform
    account_identifier: str = Field(..., description="Platform-specific user or page ID")
    account_name: str = Field(..., description="Display name or handle of the social account")
    team_id: Optional[int] = None


class SocialAccountCreate(SocialAccountBase):
    access_token: str = Field(..., description="Initial OAuth access token (will be encrypted)")
    refresh_token: Optional[str] = Field(None, description="Optional OAuth refresh token (will be encrypted)")
    token_expires_at: Optional[datetime] = None
    platform_permissions: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured permission scopes for the connected account"
    )


class SocialAccountUpdatePermissions(BaseModel):
    platform_permissions: Dict[str, Any] = Field(..., description="Updated platform permissions dictionary")


class SocialAccountResponse(SocialAccountBase):
    id: int
    user_id: int
    connection_status: SocialAccountStatus
    is_token_expired: bool = False
    token_expires_at: Optional[datetime] = None
    platform_permissions: Optional[Dict[str, Any]] = None
    last_synced_at: Optional[datetime] = None
    last_failed_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    sync_status: Optional[str] = "idle"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, account) -> "SocialAccountResponse":
        """Compute dynamic fields such as is_token_expired safely without exposing tokens."""
        is_expired = False
        if account.token_expires_at:
            is_expired = account.token_expires_at <= datetime.now(timezone.utc)

        return cls(
            id=account.id,
            user_id=account.user_id,
            team_id=account.team_id,
            platform=account.platform,
            account_identifier=account.account_identifier,
            account_name=account.account_name,
            connection_status=account.connection_status,
            is_token_expired=is_expired,
            token_expires_at=account.token_expires_at,
            platform_permissions=account.platform_permissions or {},
            last_synced_at=account.last_synced_at,
            last_failed_sync_at=getattr(account, "last_failed_sync_at", None),
            sync_error=getattr(account, "sync_error", None),
            sync_status=getattr(account, "sync_status", "idle") or "idle",
            created_at=account.created_at,
            updated_at=account.updated_at
        )


class SocialAccountStatusResponse(BaseModel):
    id: int
    platform: SocialPlatform
    account_name: str
    connection_status: SocialAccountStatus
    is_token_expired: bool
    token_expires_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None


class SocialAccountSyncResponse(BaseModel):
    account_id: int
    platform: SocialPlatform
    synced_at: datetime
    connection_status: SocialAccountStatus
    sync_status: str
    message: str


class FacebookInstagramAccount(BaseModel):
    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None


class FacebookPageItem(BaseModel):
    page_id: str
    name: str
    category: Optional[str] = None
    picture_url: Optional[str] = None
    has_instagram: bool = False
    instagram_account: Optional[FacebookInstagramAccount] = None


class FacebookPagesResponse(BaseModel):
    pages: List[FacebookPageItem]


class FacebookConnectPageRequest(BaseModel):
    session_token: str
    page_id: str
    connect_instagram: bool = False
    team_id: Optional[int] = None


class FacebookConnectPageResponse(BaseModel):
    status: str
    facebook_account: SocialAccountResponse
    instagram_account: Optional[SocialAccountResponse] = None
    message: str


class InstagramMetricSnapshotResponse(BaseModel):
    id: int
    account_id: int
    date: str
    follower_count: int
    following_count: int
    media_count: int
    net_follower_growth: int
    growth_rate: float
    impressions: int
    reach: int
    profile_views: int
    website_clicks: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstagramMediaResponse(BaseModel):
    id: int
    account_id: int
    external_media_id: str
    caption: Optional[str] = None
    media_type: str
    permalink: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    like_count: int
    comments_count: int
    views_count: int
    reach_count: int
    shares_count: int
    saved_count: int
    engagement: int
    performance_score: float
    raw_insights: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class InstagramCommentResponse(BaseModel):
    id: int
    media_id: int
    external_comment_id: str
    from_username: Optional[str] = None
    text: str
    timestamp: Optional[datetime] = None
    like_count: int
    parent_comment_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstagramCommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Comment text to post")


class InstagramScoreBreakdown(BaseModel):
    likes: int = 0
    comments: int = 0
    views: int = 0
    reach: int = 0
    saves: int = 0
    shares: int = 0
    engagement_rate: float = 0.0


class InstagramPerformanceScoreResponse(BaseModel):
    account_id: int
    score: float = Field(..., description="Deterministic SocialPilot Performance Score (0-100)")
    grade: str = Field(..., description="Tier rating: Excellent, Strong, Good, Fair, Developing")
    formula_description: str
    breakdown: InstagramScoreBreakdown

