import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class FacebookAdapter(BasePlatformAdapter):
    """
    Facebook Graph API Publishing Adapter for Pages.
    Enforces Facebook page publishing rules and 63,206 character maximums.
    """
    platform = SocialPlatform.FACEBOOK
    MAX_CHARACTERS = 63206

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
            errors.append("Facebook post must contain text content or at least one media attachment.")

        if len(effective_text) > self.MAX_CHARACTERS:
            errors.append(f"Facebook post exceeds character limit of {self.MAX_CHARACTERS}.")

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
            "message": effective_text,
            "attached_media": media_urls if media_urls else None
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute dispatch via Facebook Graph API.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live API access is absent.
        """
        logger.info(f"Dispatching Facebook post to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="Facebook Graph API integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
