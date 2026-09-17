import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class TwitterAdapter(BasePlatformAdapter):
    """
    X/Twitter API v2 Publishing Adapter.
    Enforces 280-character strict limits and media rules (max 4 images OR 1 video).
    """
    platform = SocialPlatform.TWITTER
    MAX_CHARACTERS = 280

    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        # Effective content (customization overrides base content)
        effective_text = (customization.get("content") if customization and customization.get("content") else content) or ""

        # 1. Character count validation
        char_count = len(effective_text)
        if char_count > self.MAX_CHARACTERS:
            errors.append(
                f"Twitter content exceeds {self.MAX_CHARACTERS} characters (current length: {char_count})."
            )

        if char_count == 0 and not media:
            errors.append("Twitter post must contain either text content or media.")

        # 2. Media validation
        if media:
            images = [m for m in media if m.get("file_type", "").startswith("image/")]
            videos = [m for m in media if m.get("file_type", "").startswith("video/")]

            if len(videos) > 1:
                errors.append("Twitter supports a maximum of 1 video per tweet.")
            if len(videos) == 1 and len(images) > 0:
                errors.append("Twitter does not support mixing images and video in a single tweet.")
            if len(images) > 4:
                errors.append(f"Twitter supports a maximum of 4 images per tweet (provided: {len(images)}).")

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
        effective_text = (customization.get("content") if customization and customization.get("content") else content) or ""
        media_ids = [m.get("media_id") for m in media if m.get("media_id")]

        return {
            "text": effective_text,
            "media": {"media_ids": media_ids} if media_ids else None
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute dispatch via X API v2.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live OAuth API access is absent.
        """
        # In development without live Twitter developer app keys, yield explicit non-success
        logger.info(f"Dispatching tweet to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="Twitter/X API v2 integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
