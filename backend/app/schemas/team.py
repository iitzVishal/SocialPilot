from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import UserRole
from app.schemas.user import UserResponse, EMAIL_REGEX

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="The name of the team")
    description: Optional[str] = Field(None, description="Optional description of the team")
    require_post_approval: Optional[bool] = Field(False, description="Whether this workspace requires approvals before publishing")

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="The name of the team")
    description: Optional[str] = Field(None, description="Optional description of the team")
    require_post_approval: Optional[bool] = Field(None, description="Whether this workspace requires approvals before publishing")

class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    owner_id: int
    require_post_approval: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamMemberCreate(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX, description="Email of the user to add to the team")
    role: UserRole = Field(UserRole.CONTENT_CREATOR, description="The role of the member within the team")

class TeamMemberUpdate(BaseModel):
    role: UserRole = Field(..., description="The role of the member within the team")

class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: UserRole
    created_at: datetime
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)
