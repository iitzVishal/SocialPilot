import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class FacebookAdapter(BasePlatformAdapter):
    platform = SocialPlatform.FACEBOOK

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.META_CLIENT_ID or "META_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.META_REDIRECT_URI
        scope = "public_profile,pages_show_list,pages_manage_posts"
        return f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}&redirect_uri={uri}&state={state}&scope={scope}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.META_REDIRECT_URI
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": uri,
            "code": code,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(token_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta Client ID and Client Secret must be configured in backend/.env")

        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": refresh_token,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://graph.facebook.com/me"
        params = {
            "fields": "id,name,picture.type(large)",
            "access_token": access_token
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_identifier": data.get("id", "fb_unknown"),
                "account_name": data.get("name", "Facebook Account"),
                "avatar_url": data.get("picture", {}).get("data", {}).get("url")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["public_profile", "pages_show_list", "pages_manage_posts"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"Facebook sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        try:
            url = "https://graph.facebook.com/me/permissions"
            params = {"access_token": access_token}
            with httpx.Client(timeout=5.0) as client:
                resp = client.delete(url, params=params)
                return resp.status_code == 200
        except Exception:
            return True
