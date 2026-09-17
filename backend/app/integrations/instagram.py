import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramAdapter(BasePlatformAdapter):
    platform = SocialPlatform.INSTAGRAM

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.META_CLIENT_ID or "META_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.INSTAGRAM_REDIRECT_URI
        scope = "instagram_basic,instagram_content_publish"
        return f"https://api.instagram.com/oauth/authorize?client_id={client_id}&redirect_uri={uri}&scope={scope}&response_type=code&state={state}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta/Instagram Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.INSTAGRAM_REDIRECT_URI
        token_url = "https://api.instagram.com/oauth/access_token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": uri,
            "code": code,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_secret = settings.META_CLIENT_SECRET
        if not client_secret:
            raise ValueError("Meta/Instagram Client Secret must be configured in backend/.env")

        url = "https://graph.instagram.com/refresh_access_token"
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": refresh_token,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://graph.instagram.com/me"
        params = {
            "fields": "id,username,account_type",
            "access_token": access_token
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_identifier": data.get("id", "ig_unknown"),
                "account_name": data.get("username", "Instagram Account"),
                "account_type": data.get("account_type", "PERSONAL")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["instagram_basic", "instagram_content_publish"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"Instagram sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        return True
