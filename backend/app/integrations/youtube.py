import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeAdapter(BasePlatformAdapter):
    platform = SocialPlatform.YOUTUBE

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.GOOGLE_CLIENT_ID or "GOOGLE_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        scope = "https://www.googleapis.com/auth/youtube.upload%20https://www.googleapis.com/auth/youtube.readonly%20https://www.googleapis.com/auth/userinfo.profile"
        return f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={client_id}&redirect_uri={uri}&scope={scope}&access_type=offline&prompt=consent&state={state}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Google Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": uri,
            "grant_type": "authorization_code",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Google Client credentials must be configured in backend/.env")

        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "snippet", "mine": "true"}
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    ch = items[0]
                    return {
                        "account_identifier": ch.get("id", "yt_unknown"),
                        "account_name": ch.get("snippet", {}).get("title", "YouTube Channel"),
                        "avatar_url": ch.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url")
                    }

            # Fallback to Google UserInfo profile
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            resp2 = client.get(userinfo_url, headers=headers)
            resp2.raise_for_status()
            data2 = resp2.json()
            return {
                "account_identifier": data2.get("id", "yt_unknown"),
                "account_name": data2.get("name", "YouTube Account"),
                "avatar_url": data2.get("picture")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["youtube.upload", "youtube.readonly"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"YouTube sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        try:
            url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url)
                return resp.status_code == 200
        except Exception:
            return True
