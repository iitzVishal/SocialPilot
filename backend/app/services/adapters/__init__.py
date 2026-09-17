from typing import Dict, Union
from fastapi import HTTPException, status
from app.models.enums import SocialPlatform
from app.services.adapters.base import (
    BasePlatformAdapter,
    ValidationResult,
    AdapterPublishResult,
)
from app.services.adapters.facebook import FacebookAdapter
from app.services.adapters.instagram import InstagramAdapter
from app.services.adapters.linkedin import LinkedInAdapter
from app.services.adapters.twitter import TwitterAdapter
from app.services.adapters.youtube import YouTubeAdapter
from app.services.adapters.pinterest import PinterestAdapter

# Registry mapping SocialPlatform -> concrete Adapter instance
_ADAPTER_REGISTRY: Dict[SocialPlatform, BasePlatformAdapter] = {
    SocialPlatform.FACEBOOK: FacebookAdapter(),
    SocialPlatform.INSTAGRAM: InstagramAdapter(),
    SocialPlatform.LINKEDIN: LinkedInAdapter(),
    SocialPlatform.TWITTER: TwitterAdapter(),
    SocialPlatform.YOUTUBE: YouTubeAdapter(),
    SocialPlatform.PINTEREST: PinterestAdapter(),
}


def get_platform_adapter(platform: Union[SocialPlatform, str]) -> BasePlatformAdapter:
    """
    Resolve concrete platform publishing adapter from registry.
    Raises HTTP 400 if an unsupported platform is requested.
    """
    if isinstance(platform, str):
        try:
            platform_enum = SocialPlatform(platform.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported social platform: '{platform}'"
            )
    else:
        platform_enum = platform

    adapter = _ADAPTER_REGISTRY.get(platform_enum)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No publishing adapter registered for platform: {platform_enum.value}"
        )
    return adapter


def register_custom_adapter(platform: SocialPlatform, adapter: BasePlatformAdapter) -> None:
    """Register or override an adapter (primarily used for test harnesses)."""
    _ADAPTER_REGISTRY[platform] = adapter


__all__ = [
    "BasePlatformAdapter",
    "ValidationResult",
    "AdapterPublishResult",
    "FacebookAdapter",
    "InstagramAdapter",
    "LinkedInAdapter",
    "TwitterAdapter",
    "YouTubeAdapter",
    "PinterestAdapter",
    "get_platform_adapter",
    "register_custom_adapter",
]
