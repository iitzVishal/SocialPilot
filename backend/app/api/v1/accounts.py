from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.enums import SocialPlatform, SocialAccountStatus
from app.schemas.social_account import (
    SocialAccountCreate,
    SocialAccountResponse,
    SocialAccountStatusResponse,
    SocialAccountUpdatePermissions,
    SocialAccountSyncResponse
)
from app.services import social_account_service

router = APIRouter()


@router.post("", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED, summary="Connect social media account")
def connect_account(
    account_in: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Connect a social media account.
    Access and refresh tokens are securely encrypted before persistence.
    Raw tokens are never returned in the API response.
    """
    account = social_account_service.connect_account(db, current_user, account_in)
    return SocialAccountResponse.from_orm_model(account)


@router.get("", response_model=List[SocialAccountResponse], summary="List connected social media accounts")
def list_accounts(
    platform: Optional[SocialPlatform] = Query(None, description="Filter by social media platform"),
    connection_status: Optional[SocialAccountStatus] = Query(None, description="Filter by account status"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve social media accounts accessible to the authenticated user with optional platform/status filters."""
    accounts = social_account_service.list_accounts(db, current_user, platform=platform, connection_status=connection_status, team_id=team_id)
    return [SocialAccountResponse.from_orm_model(acc) for acc in accounts]


@router.get("/{account_id}", response_model=SocialAccountResponse, summary="Get single social media account")
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve safe social account details verifying ownership/authorization."""
    account = social_account_service.get_account(db, current_user, account_id)
    return SocialAccountResponse.from_orm_model(account)


@router.delete("/{account_id}", response_model=SocialAccountResponse, summary="Disconnect social media account")
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Safely disconnect/revoke a social media account connection."""
    account = social_account_service.disconnect_account(db, current_user, account_id)
    return SocialAccountResponse.from_orm_model(account)


@router.get("/{account_id}/status", response_model=SocialAccountStatusResponse, summary="Check social account connection & token status")
def get_account_status(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check account connection status and token validity without third-party network overhead."""
    account = social_account_service.get_account(db, current_user, account_id)
    status_data = social_account_service.check_token_status(account)
    return SocialAccountStatusResponse(**status_data)


@router.patch("/{account_id}/permissions", response_model=SocialAccountResponse, summary="Update account platform permissions")
def update_permissions(
    account_id: int,
    perms_in: SocialAccountUpdatePermissions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update platform permissions for a connected social account."""
    account = social_account_service.update_account_permissions(db, current_user, account_id, perms_in)
    return SocialAccountResponse.from_orm_model(account)


@router.post("/{account_id}/sync", response_model=SocialAccountSyncResponse, summary="Trigger account synchronization")
def sync_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger the account synchronization workflow."""
    result = social_account_service.synchronize_account(db, current_user, account_id)
    return SocialAccountSyncResponse(
        account_id=result["account_id"],
        platform=result["platform"],
        synced_at=result["synced_at"],
        connection_status=result["connection_status"],
        sync_status=result["sync_status"],
        message=result["message"]
    )
