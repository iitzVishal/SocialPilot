from datetime import datetime, timezone
from typing import Optional, Dict, Any
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
