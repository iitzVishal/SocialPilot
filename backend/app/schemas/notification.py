from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType


class NotificationCreate(BaseModel):
    user_id: int
    team_id: Optional[int] = None
    type: NotificationType
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    link: Optional[str] = Field(None, max_length=512)


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    team_id: Optional[int] = None
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    count: int
