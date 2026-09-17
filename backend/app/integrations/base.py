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
