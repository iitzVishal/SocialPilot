import logging
from typing import Dict, Any, Optional, List
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramAdapter(BasePlatformAdapter):
    platform = SocialPlatform.INSTAGRAM

    @property
    def api_version(self) -> str:
        return settings.META_API_VERSION

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """
        Instagram Professional/Business accounts are discovered via the Facebook Login flow.
        The Meta App is configured as a Facebook Login app (not Instagram Basic Display API).
        We use the Facebook dialog endpoint and route to the facebook/callback, which then
        discovers linked Instagram Business accounts through the Facebook Page's
        instagram_business_account field in the Graph API.

        The INSTAGRAM_REDIRECT_URI must point to /oauth/facebook/callback (same as Facebook)
        because this flow goes through Facebook Login.
        """
        client_id = settings.META_CLIENT_ID or "META_CLIENT_ID_PLACEHOLDER"
        # Route through Facebook callback — Instagram is discovered via linked Page
        uri = redirect_uri or settings.META_REDIRECT_URI
        # Use full Facebook + Instagram scopes so both can be authorized in one flow
        base_url = (
            f"https://www.facebook.com/{self.api_version}/dialog/oauth"
            f"?client_id={client_id}"
            f"&redirect_uri={uri}"
            f"&state={state}"
            f"&response_type=code"
            f"&auth_type=rerequest"
        )
        if settings.META_CONFIG_ID and settings.META_CONFIG_ID.strip():
            return f"{base_url}&config_id={settings.META_CONFIG_ID.strip()}&override_default_response_type=true"
        scope = settings.META_OAUTH_SCOPES
        return f"{base_url}&scope={scope}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange code via the Facebook Graph API token endpoint.
        Since Instagram authorization now flows through Facebook Login,
        the code exchange happens at the Graph API endpoint (not api.instagram.com).
        """
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta/Instagram Client ID and Client Secret must be configured in backend/.env")

        # Route to the same redirect URI as the Facebook callback (Facebook Login flow)
        uri = redirect_uri or settings.META_REDIRECT_URI
        token_url = f"https://graph.facebook.com/{self.api_version}/oauth/access_token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": uri,
            "code": code,
        }
        with httpx.Client(timeout=15.0) as client:
            try:
                resp = client.get(token_url, params=params)
                data = resp.json()
            except httpx.TimeoutException:
                raise ValueError("Connection to Meta OAuth server timed out.")
            except Exception as e:
                raise ValueError(f"Failed to exchange Instagram/Meta code for token: {e}")

        if resp.status_code != 200 or "error" in data:
            err_data = data.get("error", {})
            err_msg = err_data.get("message", "Meta OAuth token exchange failed.")
            err_code = err_data.get("code")
            logger.warning(f"Instagram/Meta token exchange error [code {err_code}]: {err_msg}")
            raise ValueError(f"Meta API error: {err_msg}")

        return data

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_secret = settings.META_CLIENT_SECRET
        if not client_secret:
            raise ValueError("Meta/Instagram Client Secret must be configured in backend/.env")

        url = "https://graph.instagram.com/refresh_access_token"
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": refresh_token,
        }
        with httpx.Client(timeout=15.0) as client:
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

    def get_instagram_details(self, instagram_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch details of an Instagram Professional/Business account via Meta Graph API."""
        url = f"https://graph.facebook.com/{self.api_version}/{instagram_id}"
        params = {
            "fields": "id,username,name,profile_picture_url,followers_count,media_count",
            "access_token": access_token
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            # Query Instagram account via Meta Graph API
            url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}"
            params = {
                "fields": "id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count",
                "access_token": access_token
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                data = resp.json()

            if resp.status_code != 200 or "error" in data:
                err = data.get("error", {})
                err_code = err.get("code")
                err_subcode = err.get("error_subcode")
                err_msg = err.get("message", "Instagram synchronization failed")
                is_expired = err_code == 190 or err_subcode in (463, 467)
                is_revoked = err_subcode == 458 or "revoked" in err_msg.lower() or "session has been invalidated" in err_msg.lower()
                logger.warning(f"Instagram sync failed for {account_identifier}: code={err_code}, subcode={err_subcode}, msg={err_msg}")
                return {
                    "platform": self.platform.value,
                    "account_identifier": account_identifier,
                    "status": "error",
                    "is_token_expired": is_expired,
                    "is_revoked": is_revoked,
                    "message": f"Access revoked: {err_msg}" if is_revoked else (f"Token expired or unauthorized: {err_msg}" if is_expired else err_msg)
                }

            return {
                "platform": self.platform.value,
                "account_identifier": data.get("id", account_identifier),
                "account_name": data.get("username", "Instagram Account"),
                "username": data.get("username"),
                "biography": data.get("biography"),
                "avatar_url": data.get("profile_picture_url"),
                "follower_count": data.get("followers_count", 0),
                "following_count": data.get("follows_count", 0),
                "post_count": data.get("media_count", 0),
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

    def fetch_account_metrics(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """Fetch Instagram Business account followers and media count via Meta Graph API."""
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}"
            params = {"fields": "followers_count,media_count", "access_token": access_token}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    followers = data.get("followers_count", 0)
                    media = data.get("media_count", 0)
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "follower_count": int(followers),
                        "following_count": 0,
                        "post_count": int(media),
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": "Instagram metrics could not be retrieved from Graph API."
            }
        except Exception as e:
            logger.warning(f"Instagram fetch_account_metrics error: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": str(e)
            }

    def fetch_post_metrics(self, access_token: str, external_post_id: str) -> Dict[str, Any]:
        """Fetch Instagram media like count and comments count via Meta Graph API."""
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{external_post_id}"
            params = {"fields": "like_count,comments_count", "access_token": access_token}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    likes = data.get("like_count", 0)
                    comments = data.get("comments_count", 0)
                    total_eng = likes + comments
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "likes": likes,
                        "comments": comments,
                        "shares": 0,
                        "clicks": 0,
                        "views": None,
                        "impressions": None,
                        "reach": None,
                        "engagement_rate": None,
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": f"Instagram post {external_post_id} statistics not found."
            }
        except Exception as e:
            logger.warning(f"Instagram fetch_post_metrics error for {external_post_id}: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": str(e)
            }
    def fetch_recent_posts(self, access_token: str, account_identifier: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch recent published media from Instagram Professional account via Meta Graph API with pagination support.
        """
        posts = []
        max_posts = min(limit, 50)
        url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}/media"
        params = {
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
            "limit": min(max_posts, 25),
            "access_token": access_token
        }

        with httpx.Client(timeout=15.0) as client:
            while url and len(posts) < max_posts:
                try:
                    resp = client.get(url, params=params)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    items = data.get("data", [])
                    if not items:
                        break

                    for item in items:
                        likes = item.get("like_count", 0)
                        comments = item.get("comments_count", 0)
                        total_eng = likes + comments
                        media_type = item.get("media_type", "IMAGE").lower()
                        thumb = item.get("thumbnail_url") or item.get("media_url")

                        posts.append({
                            "external_post_id": str(item.get("id")),
                            "platform": self.platform.value,
                            "caption": item.get("caption", ""),
                            "created_time": item.get("timestamp"),
                            "permalink": item.get("permalink"),
                            "media_type": media_type,
                            "thumbnail_url": thumb,
                            "likes": likes,
                            "comments": comments,
                            "shares": 0,
                            "impressions": None,
                            "reach": None,
                            "engagement": total_eng,
                            "engagement_rate": None,
                        })

                        if len(posts) >= max_posts:
                            break

                    paging = data.get("paging", {})
                    url = paging.get("next")
                    params = None
                except Exception as e:
                    logger.warning(f"Error fetching Instagram media for {account_identifier}: {e}")
                    break

        return posts
