import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class LinkedInAdapter(BasePlatformAdapter):
    """
    LinkedIn Community Management & ugcPosts Publishing Adapter.
    Enforces 3,000 character maximums and media share structures.
    """
    platform = SocialPlatform.LINKEDIN
    MAX_CHARACTERS = 3000

    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        effective_text = (customization.get("content") if customization and customization.get("content") else content) or ""

        if len(effective_text) == 0 and (not media or len(media) == 0):
            errors.append("LinkedIn post must contain commentary text or media attachments.")

        if len(effective_text) > self.MAX_CHARACTERS:
            errors.append(f"LinkedIn commentary exceeds {self.MAX_CHARACTERS} characters (current: {len(effective_text)}).")

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
            "author": "urn:li:person:UNKNOWN",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": effective_text},
                    "shareMediaCategory": "ARTICLE" if not media_urls else "IMAGE",
                    "media": [{"originalUrl": url} for url in media_urls] if media_urls else []
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute dispatch via LinkedIn ugcPosts API.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live API access is absent.
        """
        logger.info(f"Dispatching LinkedIn post to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="LinkedIn API integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
