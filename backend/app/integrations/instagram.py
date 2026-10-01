import logging
import urllib.parse
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
        Generate Instagram OAuth authorization URL.
        Defaults to modern Instagram Business Login (https://www.instagram.com/oauth/authorize)
        with supported permissions (instagram_business_basic, instagram_business_content_publish).
        Can be switched to Facebook Login for Instagram via INSTAGRAM_AUTH_TYPE="facebook_login".
        """
        client_id = settings.META_CLIENT_ID or "META_CLIENT_ID_PLACEHOLDER"
        auth_type = getattr(settings, "INSTAGRAM_AUTH_TYPE", "instagram_login")

        if auth_type == "instagram_login":
            uri = redirect_uri or settings.INSTAGRAM_REDIRECT_URI
            scope = getattr(settings, "INSTAGRAM_OAUTH_SCOPES", "instagram_business_basic,instagram_business_content_publish")
            return (
                f"https://www.instagram.com/oauth/authorize"
                f"?enable_fb_login=0"
                f"&force_authentication=1"
                f"&client_id={client_id}"
                f"&redirect_uri={urllib.parse.quote(uri, safe='')}"
                f"&response_type=code"
                f"&scope={scope}"
                f"&state={state}"
            )
        else:
            uri = redirect_uri or settings.META_REDIRECT_URI
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
            scope = getattr(settings, "INSTAGRAM_OAUTH_SCOPES", "instagram_business_basic,instagram_business_content_publish")
            return f"{base_url}&scope={scope}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange authorization code for an Instagram access token.
        For Instagram Business Login: exchanges code at api.instagram.com,
        then upgrades to a 60-day long-lived token via graph.instagram.com.
        """
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta/Instagram Client ID and Client Secret must be configured in backend/.env")

        auth_type = getattr(settings, "INSTAGRAM_AUTH_TYPE", "instagram_login")
        if auth_type == "instagram_login":
            uri = redirect_uri or settings.INSTAGRAM_REDIRECT_URI
            token_url = "https://api.instagram.com/oauth/access_token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": uri,
                "code": code,
            }
            with httpx.Client(timeout=15.0) as client:
                try:
                    resp = client.post(token_url, data=data)
                    data_res = resp.json()
                except httpx.TimeoutException:
                    raise ValueError("Connection to Instagram OAuth server timed out.")
                except Exception as e:
                    raise ValueError(f"Failed to exchange Instagram code for token: {e}")

            if resp.status_code != 200 or "error" in data_res or "error_type" in data_res:
                err_msg = data_res.get("error_message") or data_res.get("error", {}).get("message", "Instagram OAuth token exchange failed.")
                logger.warning(f"Instagram token exchange error: {err_msg}")
                raise ValueError(f"Instagram API error: {err_msg}")

            short_lived_token = data_res.get("access_token")
            user_id = data_res.get("user_id")

            # Upgrade to long-lived access token (60 days)
            try:
                ll_url = "https://graph.instagram.com/access_token"
                ll_params = {
                    "grant_type": "ig_exchange_token",
                    "client_secret": client_secret,
                    "access_token": short_lived_token
                }
                with httpx.Client(timeout=15.0) as client:
                    ll_resp = client.get(ll_url, params=ll_params)
                    if ll_resp.status_code == 200:
                        ll_data = ll_resp.json()
                        return {
                            "access_token": ll_data.get("access_token", short_lived_token),
                            "token_type": ll_data.get("token_type", "bearer"),
                            "expires_in": ll_data.get("expires_in", 5184000),
                            "user_id": user_id
                        }
            except Exception as e:
                logger.warning(f"Long-lived Instagram token upgrade failed: {e}")

            return {
                "access_token": short_lived_token,
                "expires_in": 3600,
                "user_id": user_id
            }
        else:
            # Facebook Graph API code exchange
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
                    data_res = resp.json()
                except httpx.TimeoutException:
                    raise ValueError("Connection to Meta OAuth server timed out.")
                except Exception as e:
                    raise ValueError(f"Failed to exchange Meta code for token: {e}")

            if resp.status_code != 200 or "error" in data_res:
                err_data = data_res.get("error", {})
                err_msg = err_data.get("message", "Meta OAuth token exchange failed.")
                raise ValueError(f"Meta API error: {err_msg}")

            return data_res

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
        """
        Retrieve Instagram profile information directly from graph.instagram.com/me.
        """
        url = "https://graph.instagram.com/me"
        params = {
            "fields": "id,username,account_type,profile_picture_url,followers_count,follows_count,media_count",
            "access_token": access_token
        }
        with httpx.Client(timeout=10.0) as client:
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "account_identifier": str(data.get("id", "ig_unknown")),
                        "account_name": data.get("username", "Instagram Account"),
                        "username": data.get("username"),
                        "name": data.get("name") or data.get("username"),
                        "account_type": data.get("account_type", "BUSINESS"),
                        "avatar_url": data.get("profile_picture_url"),
                        "followers_count": data.get("followers_count"),
                        "follows_count": data.get("follows_count"),
                        "media_count": data.get("media_count")
                    }
            except Exception as e:
                logger.warning(f"Error fetching extended Instagram profile: {e}")

            # Fallback to basic fields if extended fields are restricted
            try:
                basic_params = {
                    "fields": "id,username,account_type",
                    "access_token": access_token
                }
                resp = client.get(url, params=basic_params)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "account_identifier": str(data.get("id", "ig_unknown")),
                        "account_name": data.get("username", "Instagram Account"),
                        "username": data.get("username"),
                        "name": data.get("username"),
                        "account_type": data.get("account_type", "BUSINESS"),
                        "avatar_url": None,
                        "followers_count": None,
                        "follows_count": None,
                        "media_count": None
                    }
            except Exception as e:
                logger.error(f"Error fetching basic Instagram profile: {e}")

        return {
            "account_identifier": "ig_unknown",
            "account_name": "Instagram Account",
            "username": "Instagram Account",
            "account_type": "BUSINESS"
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
            data = None
            resp_code = 500

            # 1. Try graph.instagram.com/me first (for direct Instagram Login accounts)
            try:
                url_ig = "https://graph.instagram.com/me"
                params_ig = {
                    "fields": "id,username,name,account_type,profile_picture_url,biography,followers_count,follows_count,media_count",
                    "access_token": access_token
                }
                with httpx.Client(timeout=10.0) as client:
                    resp_ig = client.get(url_ig, params=params_ig)
                    if resp_ig.status_code == 200:
                        data_ig = resp_ig.json()
                        if "id" in data_ig:
                            data = data_ig
                            resp_code = 200
            except Exception as e:
                logger.debug(f"graph.instagram.com query not applicable: {e}")

            # 2. If not retrieved, query Instagram account via Meta Graph API (for linked Page accounts)
            if not data:
                url_fb = f"https://graph.facebook.com/{self.api_version}/{account_identifier}"
                params_fb = {
                    "fields": "id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count",
                    "access_token": access_token
                }
                with httpx.Client(timeout=10.0) as client:
                    resp_fb = client.get(url_fb, params=params_fb)
                    resp_code = resp_fb.status_code
                    data = resp_fb.json()

            if resp_code != 200 or not data or "error" in data:
                err = data.get("error", {}) if data else {}
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

            scopes_list = getattr(settings, "INSTAGRAM_OAUTH_SCOPES", "instagram_business_basic,instagram_business_content_publish").split(",")
            return {
                "platform": self.platform.value,
                "account_identifier": str(data.get("id", account_identifier)),
                "account_name": data.get("username", "Instagram Account"),
                "username": data.get("username"),
                "name": data.get("name"),
                "biography": data.get("biography"),
                "avatar_url": data.get("profile_picture_url"),
                "follower_count": data.get("followers_count"),
                "following_count": data.get("follows_count"),
                "post_count": data.get("media_count"),
                "account_type": data.get("account_type", "BUSINESS"),
                "status": "synchronized",
                "scopes": scopes_list,
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
