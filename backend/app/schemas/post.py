from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.enums import SocialPlatform, PostStatus, PublishResultStatus
from app.schemas.media import MediaAttachment


class PlatformCustomization(BaseModel):
    """Platform-specific content customizations overriding or complementing base content."""
    content: Optional[str] = Field(None, description="Custom content/caption for this platform")
    media_ids: Optional[List[str]] = Field(default_factory=list, description="Specific media attachment IDs")
    title: Optional[str] = Field(None, description="Platform-specific title (e.g. YouTube/Pinterest)")
    destination_board: Optional[str] = Field(None, description="Target board identifier (Pinterest)")
    aspect_ratio_override: Optional[str] = Field(None, description="Platform-specific crop ratio")


class AccountPublishResult(BaseModel):
    """Execution status and result for an individual target social account dispatch."""
    account_id: int = Field(..., description="PostgreSQL social account ID")
    platform: SocialPlatform = Field(..., description="Platform identifier")
    status: PublishResultStatus = Field(default=PublishResultStatus.PENDING, description="Execution status")
    external_post_id: Optional[str] = Field(None, description="Official ID returned by platform API")
    error_code: Optional[str] = Field(None, description="Structured error code if failed")
    error_message: Optional[str] = Field(None, description="Human-readable error details")
    retryable: bool = Field(default=True, description="Whether failed dispatch can be retried")
    attempt_count: int = Field(default=0, ge=0, description="Total execution attempts made")
    published_at: Optional[datetime] = Field(None, description="UTC completion timestamp")


class PostBase(BaseModel):
    """Base fields for multi-platform posts."""
    title: Optional[str] = Field(None, max_length=200, description="Internal organization title")
    base_content: str = Field(..., min_length=1, max_length=10000, description="Base text content")
    media_attachments: List[MediaAttachment] = Field(default_factory=list, description="Attached media files")
    target_platforms: List[SocialPlatform] = Field(default_factory=list, description="Target social platforms")
    target_accounts: List[int] = Field(default_factory=list, description="Target social account IDs (PostgreSQL)")
    platform_customizations: Dict[str, PlatformCustomization] = Field(
        default_factory=dict,
        description="Per-platform customized text or media payloads"
    )

    @field_validator("platform_customizations")
    @classmethod
    def validate_customization_keys(cls, v: Dict[str, PlatformCustomization]) -> Dict[str, PlatformCustomization]:
        valid_platforms = {p.value for p in SocialPlatform}
        for key in v.keys():
            if key not in valid_platforms:
                raise ValueError(f"Invalid platform customization key: '{key}'. Must be one of {list(valid_platforms)}.")
        return v


class PostCreate(PostBase):
    """Schema for creating a post draft, scheduling a post, or queuing immediate publication."""
    team_id: Optional[int] = Field(None, description="Optional team ownership reference")
    campaign_id: Optional[int] = Field(None, description="Optional campaign association reference")
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled execution timestamp (UTC)")
    publish_now: bool = Field(default=False, description="Queue for immediate background publishing")

    @field_validator("scheduled_at")
    @classmethod
    def validate_future_schedule(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now_utc = datetime.now(timezone.utc)
            # Ensure timezone awareness
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= now_utc:
                raise ValueError("Scheduled timestamp must be in the future.")
        return v

    @model_validator(mode="after")
    def validate_target_accounts_on_action(self) -> "PostCreate":
        # If user requests immediate publish or scheduling, target_accounts cannot be empty
        if (self.publish_now or self.scheduled_at is not None) and len(self.target_accounts) == 0:
            raise ValueError("Target accounts must be selected when scheduling or publishing a post.")
        return self


class PostUpdate(BaseModel):
    """Schema for updating an existing post draft or modifying scheduled details."""
    title: Optional[str] = Field(None, max_length=200)
    base_content: Optional[str] = Field(None, min_length=1, max_length=10000)
    media_attachments: Optional[List[MediaAttachment]] = None
    target_platforms: Optional[List[SocialPlatform]] = None
    target_accounts: Optional[List[int]] = None
    campaign_id: Optional[int] = None
    platform_customizations: Optional[Dict[str, PlatformCustomization]] = None
    scheduled_at: Optional[datetime] = None

    @field_validator("scheduled_at")
    @classmethod
    def validate_future_update_schedule(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now_utc = datetime.now(timezone.utc)
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= now_utc:
                raise ValueError("Scheduled timestamp must be in the future.")
        return v

    @field_validator("platform_customizations")
    @classmethod
    def validate_update_customization_keys(cls, v: Optional[Dict[str, PlatformCustomization]]) -> Optional[Dict[str, PlatformCustomization]]:
        if v is not None:
            valid_platforms = {p.value for p in SocialPlatform}
            for key in v.keys():
                if key not in valid_platforms:
                    raise ValueError(f"Invalid platform customization key: '{key}'. Must be one of {list(valid_platforms)}.")
        return v


class PostScheduleRequest(BaseModel):
    """Schema for explicitly scheduling an existing draft post."""
    scheduled_at: datetime = Field(..., description="Target execution timestamp (UTC)")

    @field_validator("scheduled_at")
    @classmethod
    def validate_future_timestamp(cls, v: datetime) -> datetime:
        now_utc = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now_utc:
            raise ValueError("Scheduled timestamp must be in the future.")
        return v


class PostRejectRequest(BaseModel):
    """Schema for rejecting a post pending approval."""
    reason: str = Field(..., min_length=1, description="Reason for rejecting the post")


class PostResponse(BaseModel):
    """Clean public API response for Post documents."""
    id: str = Field(..., description="MongoDB string document ID")
    user_id: int = Field(..., description="Author PostgreSQL user ID")
    team_id: Optional[int] = None
    campaign_id: Optional[int] = None
    title: Optional[str] = None
    base_content: str
    media_attachments: List[MediaAttachment] = Field(default_factory=list)
    target_platforms: List[SocialPlatform] = Field(default_factory=list)
    target_accounts: List[int] = Field(default_factory=list)
    platform_customizations: Dict[str, PlatformCustomization] = Field(default_factory=dict)
    status: PostStatus
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    publish_results: Dict[str, AccountPublishResult] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    approval_requested_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
