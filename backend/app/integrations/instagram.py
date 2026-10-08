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

    def fetch_account_insights(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """
        Fetch Instagram Business account insights (impressions, reach, profile views, website clicks).
        Returns actual Meta API values or 0s when unsupported/permission restricted without faking.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}/insights"
        params = {
            "metric": "impressions,reach,profile_views,website_clicks",
            "period": "day",
            "access_token": access_token
        }
        res_data = {"impressions": 0, "reach": 0, "profile_views": 0, "website_clicks": 0, "supported": False}
        with httpx.Client(timeout=12.0) as client:
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    metrics_list = data.get("data", [])
                    for m in metrics_list:
                        name = m.get("name")
                        values = m.get("values", [])
                        val = values[-1].get("value", 0) if values else 0
                        if name in res_data:
                            res_data[name] = int(val)
                    res_data["supported"] = True
                else:
                    logger.info(f"Instagram insights endpoint returned {resp.status_code} for {account_identifier}")
            except Exception as e:
                logger.warning(f"Error fetching Instagram insights for {account_identifier}: {e}")
        return res_data

    def fetch_media_insights(self, access_token: str, external_media_id: str) -> Dict[str, Any]:
        """
        Fetch media-specific insights (reach, saved, shares, total_interactions) from Meta Graph API.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{external_media_id}/insights"
        params = {
            "metric": "reach,saved,shares,total_interactions",
            "access_token": access_token
        }
        insights = {"reach": 0, "saved": 0, "shares": 0, "views": 0, "supported": False}
        with httpx.Client(timeout=10.0) as client:
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", []):
                        name = item.get("name")
                        vals = item.get("values", [])
                        val = vals[0].get("value", 0) if vals else 0
                        if name == "reach":
                            insights["reach"] = int(val)
                        elif name == "saved":
                            insights["saved"] = int(val)
                        elif name == "shares":
                            insights["shares"] = int(val)
                    insights["supported"] = True
            except Exception as e:
                logger.debug(f"Media insights unavailable for {external_media_id}: {e}")
        return insights

    def create_media_container(
        self,
        access_token: str,
        account_identifier: str,
        media_type: str,
        media_url: str,
        caption: str = "",
        is_carousel_item: bool = False,
        children: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Step 1 of Instagram Graph API publishing: Create an item container.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}/media"
        data: Dict[str, Any] = {
            "access_token": access_token
        }

        if children:
            data["media_type"] = "CAROUSEL"
            data["children"] = ",".join(children)
            if caption:
                data["caption"] = caption
        elif media_type.upper() in ("VIDEO", "REELS", "REEL"):
            data["media_type"] = "REELS"
            data["video_url"] = media_url
            if caption:
                data["caption"] = caption
            if is_carousel_item:
                data["is_carousel_item"] = "true"
        else:
            data["image_url"] = media_url
            if caption:
                data["caption"] = caption
            if is_carousel_item:
                data["is_carousel_item"] = "true"

        with httpx.Client(timeout=20.0) as client:
            try:
                resp = client.post(url, data=data)
                res_json = resp.json()
            except httpx.TimeoutException:
                raise ValueError("Meta API timed out while creating Instagram media container.")
            except Exception as e:
                raise ValueError(f"Failed to communicate with Meta API: {e}")

        if resp.status_code != 200 or "error" in res_json:
            err = res_json.get("error", {})
            err_msg = err.get("message", "Failed to create media container.")
            code = err.get("code")
            subcode = err.get("error_subcode")
            logger.error(f"Meta create container error: code={code}, subcode={subcode}, msg={err_msg}")
            raise ValueError(f"Meta Graph API error ({code}): {err_msg}")

        return res_json

    def check_container_status(self, access_token: str, container_id: str) -> Dict[str, Any]:
        """
        Check container upload status before publishing (especially for video/reels).
        Status codes: EXPIRED, ERROR, FINISHED, IN_PROGRESS.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": access_token
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                raise ValueError(f"Container status check failed with HTTP {resp.status_code}")
            return resp.json()

    def publish_media_container(self, access_token: str, account_identifier: str, container_id: str) -> Dict[str, Any]:
        """
        Step 2 of Instagram Graph API publishing: Publish the container.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}/media_publish"
        data = {
            "creation_id": container_id,
            "access_token": access_token
        }
        with httpx.Client(timeout=25.0) as client:
            try:
                resp = client.post(url, data=data)
                res_json = resp.json()
            except httpx.TimeoutException:
                raise ValueError("Meta API timed out while publishing media container.")
            except Exception as e:
                raise ValueError(f"Meta publish request error: {e}")

        if resp.status_code != 200 or "error" in res_json:
            err = res_json.get("error", {})
            err_msg = err.get("message", "Failed to publish media container.")
            code = err.get("code")
            logger.error(f"Meta media_publish error: code={code}, msg={err_msg}")
            raise ValueError(f"Meta Graph API publish error ({code}): {err_msg}")

        return res_json

    def fetch_media_comments(self, access_token: str, external_media_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch comments for a media post where Meta API permissions allow.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{external_media_id}/comments"
        params = {
            "fields": "id,text,timestamp,username,like_count",
            "limit": min(limit, 50),
            "access_token": access_token
        }
        comments = []
        with httpx.Client(timeout=12.0) as client:
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for c in data.get("data", []):
                        comments.append({
                            "external_comment_id": str(c.get("id")),
                            "text": c.get("text", ""),
                            "timestamp": c.get("timestamp"),
                            "username": c.get("username"),
                            "like_count": c.get("like_count", 0)
                        })
            except Exception as e:
                logger.warning(f"Error fetching comments for media {external_media_id}: {e}")
        return comments

    def reply_to_comment(self, access_token: str, target_id: str, message: str) -> Dict[str, Any]:
        """
        Post a comment or reply to an existing comment on Instagram via Meta Graph API.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{target_id}/comments"
        data = {
            "message": message,
            "access_token": access_token
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, data=data)
            res_json = resp.json()
            if resp.status_code != 200 or "error" in res_json:
                err_msg = res_json.get("error", {}).get("message", "Failed to post comment.")
                raise ValueError(f"Meta comment error: {err_msg}")
            return res_json

