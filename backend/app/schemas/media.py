from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MediaAttachment(BaseModel):
    """Embedded media metadata attached directly to a post payload."""
    media_id: str = Field(..., description="Unique media reference UUID")
    url: str = Field(..., description="Accessible public or storage URL")
    file_name: str = Field(..., description="Original asset filename")
    file_type: str = Field(..., description="MIME type (e.g. image/jpeg, video/mp4)")
    file_size: int = Field(..., ge=0, description="File size in bytes (must be non-negative)")
    width: Optional[int] = Field(None, gt=0, description="Image/video pixel width")
    height: Optional[int] = Field(None, gt=0, description="Image/video pixel height")
    aspect_ratio: Optional[str] = Field(None, description="Aspect ratio string (e.g. 1:1, 16:9, 1.91:1)")
    alt_text: Optional[str] = Field(None, max_length=500, description="Accessibility description")

    @field_validator("file_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        allowed_prefixes = ("image/", "video/")
        if not any(v.lower().startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f"Unsupported media MIME type: {v}. Must be an image or video.")
        return v.lower()


class MediaAssetBase(BaseModel):
    """Core media asset fields."""
    file_name: str = Field(..., description="Original file name")
    mime_type: str = Field(..., description="MIME content type")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    width: Optional[int] = Field(None, gt=0, description="Pixel width")
    height: Optional[int] = Field(None, gt=0, description="Pixel height")
    aspect_ratio: Optional[str] = Field(None, description="Computed aspect ratio")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Video duration in seconds")


class MediaAssetCreate(MediaAssetBase):
    """Internal model for creating media assets in MongoDB."""
    media_id: str = Field(..., description="Unique media UUID")
    user_id: int = Field(..., description="PostgreSQL User ID owner")
    team_id: Optional[int] = Field(None, description="Optional PostgreSQL Team ID")
    storage_path: str = Field(..., description="Internal storage path on disk or cloud")
    public_url: str = Field(..., description="Publicly accessible URL")


class MediaAssetResponse(MediaAssetBase):
    """Public API response for uploaded media assets."""
    id: str = Field(..., description="MongoDB document identifier string")
    media_id: str = Field(..., description="Unique media reference UUID")
    user_id: int = Field(..., description="Owner user ID")
    team_id: Optional[int] = None
    public_url: str = Field(..., description="Accessible asset URL")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
