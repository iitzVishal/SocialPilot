from typing import Dict, Type
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.integrations.facebook import FacebookAdapter
from app.integrations.instagram import InstagramAdapter
from app.integrations.linkedin import LinkedInAdapter
from app.integrations.twitter import TwitterAdapter
from app.integrations.youtube import YouTubeAdapter
from app.integrations.pinterest import PinterestAdapter

_ADAPTER_MAP: Dict[SocialPlatform, Type[BasePlatformAdapter]] = {
    SocialPlatform.FACEBOOK: FacebookAdapter,
    SocialPlatform.INSTAGRAM: InstagramAdapter,
    SocialPlatform.LINKEDIN: LinkedInAdapter,
    SocialPlatform.TWITTER: TwitterAdapter,
    SocialPlatform.YOUTUBE: YouTubeAdapter,
    SocialPlatform.PINTEREST: PinterestAdapter,
}


def get_platform_adapter(platform: SocialPlatform) -> BasePlatformAdapter:
    """Factory function returning the platform adapter instance for a given SocialPlatform."""
    adapter_cls = _ADAPTER_MAP.get(platform)
    if not adapter_cls:
        raise ValueError(f"No integration adapter registered for platform: {platform}")
    return adapter_cls()


__all__ = [
    "BasePlatformAdapter",
    "FacebookAdapter",
    "InstagramAdapter",
    "LinkedInAdapter",
    "TwitterAdapter",
    "YouTubeAdapter",
    "PinterestAdapter",
    "get_platform_adapter",
]
