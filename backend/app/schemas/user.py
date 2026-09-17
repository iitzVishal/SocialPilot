from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import UserRole

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserBase(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX, description="User email address")
    full_name: Optional[str] = None


class UserRegister(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX, description="User email address")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX, description="User email address")
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token / Credential")


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    auth_provider: Optional[str] = "email"
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

