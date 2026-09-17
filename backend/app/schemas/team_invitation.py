from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import UserRole, TeamInvitationStatus
from app.schemas.user import UserResponse, EMAIL_REGEX
from app.schemas.team import TeamResponse


class TeamInvitationCreate(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX, description="Email of the user to invite")
    role: UserRole = Field(UserRole.CONTENT_CREATOR, description="The role of the invited member")


class TeamInvitationResponse(BaseModel):
    id: int
    team_id: int
    email: str
    role: UserRole
    invited_by_id: int
    status: TeamInvitationStatus
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    invited_by: Optional[UserResponse] = None
    team: Optional[TeamResponse] = None
    token: Optional[str] = None  # Raw token returned only on creation / dev endpoints for verification

    model_config = ConfigDict(from_attributes=True)
