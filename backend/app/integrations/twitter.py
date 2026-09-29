import logging
from typing import Dict, Any, Optional
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class TwitterAdapter(BasePlatformAdapter):
    platform = SocialPlatform.TWITTER

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.X_CLIENT_ID or "X_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.X_REDIRECT_URI
        scope = "tweet.read%20tweet.write%20users.read%20offline.access"
        return f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={uri}&scope={scope}&state={state}&code_challenge=challenge&code_challenge_method=plain"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.X_CLIENT_ID
        client_secret = settings.X_CLIENT_SECRET
        if not client_id:
            raise ValueError("X/Twitter Client ID must be configured in backend/.env")

        uri = redirect_uri or settings.X_REDIRECT_URI
        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": uri,
            "code_verifier": "challenge",
            "client_id": client_id,
        }
        auth = (client_id, client_secret) if client_secret else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data, headers=headers, auth=auth)
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.X_CLIENT_ID
        client_secret = settings.X_CLIENT_SECRET
        if not client_id:
            raise ValueError("X/Twitter Client ID must be configured in backend/.env")

        url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
        auth = (client_id, client_secret) if client_secret else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=data, headers=headers, auth=auth)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = "https://api.twitter.com/2/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"user.fields": "profile_image_url,name,username"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return {
                "account_identifier": data.get("id", "x_unknown"),
                "account_name": f"@{data.get('username', 'user')} ({data.get('name', 'X User')})",
                "avatar_url": data.get("profile_image_url")
            }

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            profile = self.get_user_profile(access_token)
            return {
                "platform": self.platform.value,
                "account_identifier": profile["account_identifier"],
                "account_name": profile["account_name"],
                "status": "synchronized",
                "scopes": ["tweet.read", "tweet.write", "users.read"],
                "external_sync": True,
            }
        except Exception as e:
            logger.warning(f"X/Twitter sync failed for {account_identifier}: {e}")
            return {
                "platform": self.platform.value,
                "account_identifier": account_identifier,
                "status": "error",
                "message": str(e)
            }

    def revoke_access(self, access_token: str) -> bool:
        return True

    def fetch_account_metrics(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """Fetch X/Twitter follower and following metrics via X API v2."""
        try:
            url = "https://api.twitter.com/2/users/me"
            params = {"user.fields": "public_metrics"}
            headers = {"Authorization": f"Bearer {access_token}"}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    metrics = resp.json().get("data", {}).get("public_metrics", {})
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "follower_count": int(metrics.get("followers_count", 0)),
                        "following_count": int(metrics.get("following_count", 0)),
                        "post_count": int(metrics.get("tweet_count", 0)),
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": "X public metrics could not be retrieved from API response."
            }
        except Exception as e:
            logger.warning(f"Twitter fetch_account_metrics error: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": str(e)
            }

    def fetch_post_metrics(self, access_token: str, external_post_id: str) -> Dict[str, Any]:
        """Fetch X/Twitter tweet public metrics via X API v2."""
        try:
            url = f"https://api.twitter.com/2/tweets/{external_post_id}"
            params = {"tweet.fields": "public_metrics"}
            headers = {"Authorization": f"Bearer {access_token}"}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    metrics = resp.json().get("data", {}).get("public_metrics", {})
                    likes = metrics.get("like_count", 0)
                    retweets = metrics.get("retweet_count", 0)
                    replies = metrics.get("reply_count", 0)
                    impressions = metrics.get("impression_count", 0)
                    total_eng = likes + retweets + replies
                    eng_rate = round((total_eng / impressions * 100), 2) if impressions > 0 else 0.0
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "likes": likes,
                        "comments": replies,
                        "shares": retweets,
                        "clicks": 0,
                        "views": impressions,
                        "impressions": impressions,
                        "reach": impressions,
                        "engagement_rate": eng_rate,
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": f"Tweet {external_post_id} statistics not found on X."
            }
        except Exception as e:
            logger.warning(f"Twitter fetch_post_metrics error for {external_post_id}: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": str(e)
            }

