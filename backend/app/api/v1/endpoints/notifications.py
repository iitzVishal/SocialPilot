from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.enums import NotificationType
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread: Optional[bool] = Query(None, description="Filter by unread status"),
    type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Retrieve paginated notifications for the authenticated user."""
    is_read_filter = False if unread is True else (True if unread is False else None)
    return NotificationService.get_user_notifications(
        db=db,
        user=current_user,
        is_read=is_read_filter,
        type_filter=type,
        page=page,
        limit=limit
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Return the unread notification count for the authenticated user."""
    count = NotificationService.get_unread_count(db=db, user=current_user)
    return {"count": count}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Mark a single notification owned by the authenticated user as read."""
    return NotificationService.mark_as_read(
        db=db,
        user=current_user,
        notification_id=notification_id
    )


@router.patch("/read-all", response_model=Dict[str, Any])
def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Mark all unread notifications for the authenticated user as read."""
    count = NotificationService.mark_all_as_read(db=db, user=current_user)
    return {
        "status": "success",
        "message": f"Marked {count} notifications as read.",
        "count": count
    }
