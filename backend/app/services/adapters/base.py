from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount


class ValidationResult(BaseModel):
    """Structured validation output containing pass/fail state and detailed errors/warnings."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AdapterPublishResult(BaseModel):
    """
    Authoritative publishing response model.
    Guarantees strict structured errors and enforces zero fake publishing.
    """
    platform: SocialPlatform
    status: PublishResultStatus
    external_post_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = False
    published_at: Optional[datetime] = None


class BasePlatformAdapter(ABC):
    """
    Abstract Integration Adapter for Social Media Publishing.
    Defines strict contracts for validation, payload transformation, and external dispatch.
    """
    platform: SocialPlatform

    @abstractmethod
    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate platform-specific character limits, media counts, and mandatory metadata.
        Returns:
            ValidationResult(is_valid=True/False, errors=[...], warnings=[...])
        """
        pass

    @abstractmethod
    def format_payload(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transform shared content and media into platform-specific API payloads.
        """
        pass

    @abstractmethod
    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute API dispatch to external platform.
        MUST NEVER return fake success or synthetic post IDs when API access is unconfigured.
        """
        pass
