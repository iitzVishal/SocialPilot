import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class InstagramAdapter(BasePlatformAdapter):
    """
    Instagram Graph API Publishing Adapter.
    Requires at least one media item (photo/video/carousel), enforces 2,200 char caption limit.
    """
    platform = SocialPlatform.INSTAGRAM
    MAX_CAPTION_LENGTH = 2200
    MAX_CAROUSEL_ITEMS = 10

    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        effective_text = (customization.get("content") if customization and customization.get("content") else content) or ""

        # 1. Media is strictly required for Instagram
        if not media or len(media) == 0:
            errors.append("Instagram requires at least 1 media attachment (photo or video). Text-only posts are not supported.")

        if media and len(media) > self.MAX_CAROUSEL_ITEMS:
            errors.append(f"Instagram supports a maximum of {self.MAX_CAROUSEL_ITEMS} media items in a carousel (provided: {len(media)}).")

        # 2. Caption length check
        if len(effective_text) > self.MAX_CAPTION_LENGTH:
            errors.append(f"Instagram caption exceeds {self.MAX_CAPTION_LENGTH} characters (current length: {len(effective_text)}).")

        # 3. Hashtags check
        hashtag_count = effective_text.count("#")
        if hashtag_count > 30:
            errors.append(f"Instagram supports a maximum of 30 hashtags per post (current: {hashtag_count}).")

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
        media_urls = [m.get("url") for m in media if m.get("url")]

        return {
            "caption": effective_text,
            "media_type": "CAROUSEL" if len(media_urls) > 1 else ("VIDEO" if media and media[0].get("file_type", "").startswith("video/") else "IMAGE"),
            "media_urls": media_urls
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute dispatch via Instagram Graph API.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live API access is absent.
        """
        logger.info(f"Dispatching Instagram post to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="Instagram Graph API integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
