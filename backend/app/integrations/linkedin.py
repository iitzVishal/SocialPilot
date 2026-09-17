import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInAdapter(BasePlatformAdapter):
    platform = SocialPlatform.LINKEDIN

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.LINKEDIN_CLIENT_ID or "LINKEDIN_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.LINKEDIN_REDIRECT_URI
        scope = "openid%20profile%20w_member_social%20email"
        return f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={client_id}&redirect_uri={uri}&state={state}&scope={scope}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.LINKEDIN_CLIENT_ID
        client_secret = settings.LINKEDIN_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("LinkedIn Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.LINKEDIN_REDIRECT_URI
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.LINKEDIN_CLIENT_ID
        client_secret = settings.LINKEDIN_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("LinkedIn Client credentials must be configured in backend/.env")

        url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_identifier": data.get("sub", "li_unknown"),
                "account_name": data.get("name", "LinkedIn User"),
                "avatar_url": data.get("picture")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["openid", "profile", "w_member_social"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"LinkedIn sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        return True
