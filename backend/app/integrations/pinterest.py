import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class PinterestAdapter(BasePlatformAdapter):
    platform = SocialPlatform.PINTEREST

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.PINTEREST_CLIENT_ID or "PINTEREST_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.PINTEREST_REDIRECT_URI
        scope = "boards:read,pins:read,pins:write,user_accounts:read"
        return f"https://www.pinterest.com/oauth/?consumer_id={client_id}&redirect_uri={uri}&response_type=code&scope={scope}&state={state}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.PINTEREST_CLIENT_ID
        client_secret = settings.PINTEREST_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Pinterest Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.PINTEREST_REDIRECT_URI
        token_url = "https://api.pinterest.com/v5/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data, headers=headers, auth=(client_id, client_secret))
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.PINTEREST_CLIENT_ID
        client_secret = settings.PINTEREST_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Pinterest Client credentials must be configured in backend/.env")

        url = "https://api.pinterest.com/v5/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=data, headers=headers, auth=(client_id, client_secret))
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://api.pinterest.com/v5/user_account"
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_identifier": data.get("username", "pin_unknown"),
                "account_name": data.get("username", "Pinterest User"),
                "avatar_url": data.get("profile_image")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["boards:read", "pins:read", "pins:write"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"Pinterest sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        return True
