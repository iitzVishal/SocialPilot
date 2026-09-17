from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import SocialPlatform, CampaignStatus


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, max_length=2000, description="Campaign description")
    objective: Optional[str] = Field(None, max_length=255, description="Campaign objective")
    target_platforms: List[SocialPlatform] = Field(default_factory=list, description="Target platforms")
    start_date: Optional[datetime] = Field(None, description="Campaign start date")
    end_date: Optional[datetime] = Field(None, description="Campaign end date")
    budget: Optional[float] = Field(0.0, ge=0.0, description="Allocated budget")
    status: Optional[CampaignStatus] = Field(CampaignStatus.DRAFT, description="Initial campaign status")

    @model_validator(mode="after")
    def validate_dates(self) -> "CampaignCreate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    objective: Optional[str] = Field(None, max_length=255)
    target_platforms: Optional[List[SocialPlatform]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0.0)
    status: Optional[CampaignStatus] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "CampaignUpdate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class CampaignResponse(BaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str] = None
    objective: Optional[str] = None
    target_platforms: List[str] = Field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = 0.0
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    post_count: int = 0
    published_post_count: int = 0
    scheduled_post_count: int = 0

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CampaignListResponse(BaseModel):
    items: List[CampaignResponse]
    total: int
    page: int
    limit: int
    total_pages: int
