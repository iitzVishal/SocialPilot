from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.enums import SocialPlatform


class BasePlatformAdapter(ABC):
    """
    Abstract Integration Adapter for social media platform APIs.
    Defines the contract for OAuth authorization, token refreshing, and profile synchronization.
    """
    platform: SocialPlatform

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Construct the official platform OAuth 2.0 authorization URL."""
        pass

    @abstractmethod
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for access and refresh tokens."""
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Request a refreshed access token using a valid refresh token."""
        pass

    @abstractmethod
    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """Fetch remote account metadata, permissions, and profile verification."""
        pass

    @abstractmethod
    def revoke_access(self, access_token: str) -> bool:
        """Revoke application authorization on the remote platform."""
        pass

    def fetch_account_metrics(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """Fetch remote account-level audience & follower metrics."""
        return {
            "supported": False,
            "platform": self.platform.value,
            "follower_count": 0,
            "following_count": 0,
            "post_count": 0,
            "notice": f"Account metrics not supported or unconfigured for {self.platform.value}"
        }

    def fetch_post_metrics(self, access_token: str, external_post_id: str) -> Dict[str, Any]:
        """Fetch post-level engagement and reach metrics from platform API."""
        return {
            "supported": False,
            "platform": self.platform.value,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "clicks": 0,
            "views": 0,
            "impressions": 0,
            "reach": 0,
            "engagement_rate": 0.0,
            "notice": f"Post metrics not supported or unconfigured for {self.platform.value}"
        }

    def fetch_recent_posts(self, access_token: str, account_identifier: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch recent published posts/media from the platform API."""
        return []

