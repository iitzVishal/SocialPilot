import logging
from typing import Optional, List, Dict, Any
from app.models.enums import SocialPlatform, PublishResultStatus
from app.models.social_account import SocialAccount
from app.services.adapters.base import BasePlatformAdapter, ValidationResult, AdapterPublishResult

logger = logging.getLogger(__name__)


class PinterestAdapter(BasePlatformAdapter):
    """
    Pinterest API v5 Pin Creation Adapter.
    Requires at least one media image and a mandatory destination board ID.
    """
    platform = SocialPlatform.PINTEREST
    MAX_DESCRIPTION_LENGTH = 500
    MAX_TITLE_LENGTH = 100

    def validate_content(
        self,
        content: str,
        media: List[Dict[str, Any]],
        customization: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        # 1. Media is mandatory for Pinterest Pins
        if not media or len(media) == 0:
            errors.append("Pinterest requires at least 1 image or video to create a Pin.")

        # 2. Destination board is mandatory
        board = customization.get("destination_board") if customization else None
        if not board or not str(board).strip():
            errors.append("Pinterest requires a destination board identifier in platform customization.")

        # 3. Text length checks
        description = (customization.get("content") if customization and customization.get("content") else content) or ""
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(f"Pinterest Pin description exceeds {self.MAX_DESCRIPTION_LENGTH} characters.")

        title = (customization.get("title") if customization else None) or ""
        if len(title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Pinterest Pin title exceeds {self.MAX_TITLE_LENGTH} characters.")

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
        title = (customization.get("title") if customization else None) or ""
        description = (customization.get("content") if customization and customization.get("content") else content) or ""
        board_id = (customization.get("destination_board") if customization else None) or ""
        media_urls = [m.get("url") for m in media if m.get("url")]

        return {
            "title": title,
            "description": description,
            "board_id": board_id,
            "media_source": {
                "source_type": "image_url",
                "url": media_urls[0] if media_urls else None
            }
        }

    async def publish(
        self,
        social_account: SocialAccount,
        payload: Dict[str, Any]
    ) -> AdapterPublishResult:
        """
        Execute Pin dispatch via Pinterest API v5.
        Guarantees zero fake publishing: reports NOT_CONFIGURED when live API access is absent.
        """
        logger.info(f"Dispatching Pinterest pin to account {social_account.id} ({social_account.account_name})")
        return AdapterPublishResult(
            platform=self.platform,
            status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
            error_code="NOT_CONFIGURED",
            error_message="Pinterest API v5 integration is not configured with live credentials.",
            retryable=False,
            external_post_id=None
        )
