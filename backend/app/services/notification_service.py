import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.notification import Notification
from app.models.enums import NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        type: NotificationType,
        title: str,
        message: str,
        team_id: Optional[int] = None,
        link: Optional[str] = None
    ) -> Optional[Notification]:
        """Create a single persistent notification for a user."""
        try:
            notification = Notification(
                user_id=user_id,
                team_id=team_id,
                type=type,
                title=title,
                message=message,
                link=link,
                is_read=False
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def create_notifications_for_users(
        db: Session,
        user_ids: List[int],
        type: NotificationType,
        title: str,
        message: str,
        team_id: Optional[int] = None,
        link: Optional[str] = None
    ) -> List[Notification]:
        """Bulk create persistent notifications for multiple users."""
        if not user_ids:
            return []
        created = []
        try:
            for uid in set(user_ids):
                notif = Notification(
                    user_id=uid,
                    team_id=team_id,
                    type=type,
                    title=title,
                    message=message,
                    link=link,
                    is_read=False
                )
                db.add(notif)
                created.append(notif)
            db.commit()
            for n in created:
                db.refresh(n)
            return created
        except Exception as e:
            logger.error(f"Failed to bulk create notifications: {e}")
            db.rollback()
            return []

    @staticmethod
    def get_user_notifications(
        db: Session,
        user: User,
        is_read: Optional[bool] = None,
        type_filter: Optional[NotificationType] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Retrieve paginated notifications for the authenticated user."""
        query = db.query(Notification).filter(Notification.user_id == user.id)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if type_filter is not None:
            query = query.filter(Notification.type == type_filter)

        total = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count()

        total_pages = max(1, (total + limit - 1) // limit)
        offset = (page - 1) * limit
        items = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "items": items,
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

    @staticmethod
    def get_unread_count(db: Session, user: User) -> int:
        """Return the unread notification count for the authenticated user."""
        return db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count()

    @staticmethod
    def mark_as_read(db: Session, user: User, notification_id: int) -> Notification:
        """Mark a single notification owned by the current user as read."""
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification with ID {notification_id} not found."
            )

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)

        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user: User) -> int:
        """Mark all unread notifications for the authenticated user as read."""
        now = datetime.now(timezone.utc)
        count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).update(
            {Notification.is_read: True, Notification.read_at: now},
            synchronize_session=False
        )
        db.commit()
        return count
