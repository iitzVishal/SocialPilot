import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class YouTubeAdapter(BasePlatformAdapter):
    """
    YouTube Data API v3 Publishing Adapter.
    Requires at least one video attachment and a mandatory video title (max 100 chars).
    """
    platform = SocialPlatform.YOUTUBE
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 5000

    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        # 1. Video attachment is mandatory
        videos = [m for m in media if m.get("file_type", "").startswith("video/")]
        if not videos:
            errors.append("YouTube publishing requires at least 1 video attachment (.mp4).")

        # 2. Title is mandatory
        title = (customization.get("title") if customization else None) or ""
        if not title.strip():
            errors.append("YouTube requires a non-empty video title.")
        elif len(title) > self.MAX_TITLE_LENGTH:
            errors.append(f"YouTube video title exceeds {self.MAX_TITLE_LENGTH} characters (current: {len(title)}).")

        # 3. Description length check
        description = (customization.get("content") if customization and customization.get("content") else content) or ""
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(f"YouTube video description exceeds {self.MAX_DESCRIPTION_LENGTH} characters.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def format_payload(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        title = (customization.get("title") if customization else None) or "Untitled Video"
        description = (customization.get("content") if customization and customization.get("content") else content) or ""
        videos = [m for m in media if m.get("file_type", "").startswith("video/")]

        return {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22"  # People & Blogs default
            },
            "status": {
                "privacyStatus": "public"
            },
            "video_url": videos[0].get("url") if videos else None
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute video upload dispatch via YouTube Data API v3.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live API access is absent.
        """
        logger.info(f"Dispatching YouTube video to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="YouTube Data API v3 integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
