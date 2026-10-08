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
        Execute real dispatch via Instagram Graph API using the 2-step container workflow.
        Guarantees zero fake publishing: fails cleanly if live credentials or permissions are missing.
        """
        import asyncio
        from datetime import datetime, timezone
        from app.core.security import decrypt_token
        from app.integrations import get_platform_adapter

        logger.info(f"Dispatching Instagram post to account {social_account.id} (@{social_account.account_name})")

        if social_account.platform != self.platform:
            return AdapterPublishResult(
                platform=self.platform,
                status=PublishResultStatus.PENDING_EXTERNAL_INTEGRATION,
                error_code="NOT_CONFIGURED",
                error_message=f"Instagram adapter is not configured for account platform {social_account.platform}. Direct Instagram connection required.",
                retryable=False,
                external_post_id=None
            )

        if not social_account.access_token:
            return AdapterPublishResult(
                platform=self.platform,
                status=PublishResultStatus.FAILED,
                error_code="TOKEN_MISSING",
                error_message="Instagram access token is missing.",
                retryable=False
            )

        try:
            token = decrypt_token(social_account.access_token)
        except Exception as e:
            logger.warning(f"Failed to decrypt Instagram token: {e}")
            token = social_account.access_token

        media_urls = payload.get("media_urls", [])
        media_type = payload.get("media_type", "IMAGE")
        caption = payload.get("caption", "")

        if not media_urls:
            return AdapterPublishResult(
                platform=self.platform,
                status=PublishResultStatus.FAILED,
                error_code="MEDIA_REQUIRED",
                error_message="Instagram posts require at least one public image or video URL.",
                retryable=False
            )

        adapter = get_platform_adapter(SocialPlatform.INSTAGRAM)
        account_id = social_account.account_identifier

        try:
            # 1. Create Media Container
            if media_type == "CAROUSEL" and len(media_urls) > 1:
                # Step 1a: Create child containers
                child_container_ids = []
                for m_url in media_urls[:10]:
                    child_res = adapter.create_media_container(
                        access_token=token,
                        account_identifier=account_id,
                        media_type="IMAGE",
                        media_url=m_url,
                        is_carousel_item=True
                    )
                    child_id = child_res.get("id")
                    if not child_id:
                        raise ValueError("Failed to create carousel item container.")
                    child_container_ids.append(child_id)

                # Step 1b: Create carousel container
                carousel_res = adapter.create_media_container(
                    access_token=token,
                    account_identifier=account_id,
                    media_type="CAROUSEL",
                    media_url="",
                    caption=caption,
                    children=child_container_ids
                )
                container_id = carousel_res.get("id")
            else:
                primary_url = media_urls[0]
                container_res = adapter.create_media_container(
                    access_token=token,
                    account_identifier=account_id,
                    media_type=media_type,
                    media_url=primary_url,
                    caption=caption
                )
                container_id = container_res.get("id")

            if not container_id:
                raise ValueError("Meta API did not return a valid container ID.")

            # If video/reel, wait briefly for encoding
            if media_type in ("VIDEO", "REELS", "REEL"):
                await asyncio.sleep(3)

            # 2. Publish Container
            pub_res = adapter.publish_media_container(
                access_token=token,
                account_identifier=account_id,
                container_id=container_id
            )
            external_media_id = pub_res.get("id")

            if not external_media_id:
                raise ValueError("Meta API did not return published media ID.")

            logger.info(f"Successfully published Instagram post {external_media_id} for account {social_account.id}")
            return AdapterPublishResult(
                platform=self.platform,
                status=PublishResultStatus.SUCCESS,
                external_post_id=str(external_media_id),
                published_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            err_str = str(e)
            logger.error(f"Instagram publishing error for account {social_account.id}: {err_str}")
            is_retryable = "timeout" in err_str.lower() or "rate limit" in err_str.lower()
            return AdapterPublishResult(
                platform=self.platform,
                status=PublishResultStatus.FAILED,
                error_code="META_API_ERROR",
                error_message=err_str,
                retryable=is_retryable
            )

