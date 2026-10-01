import logging
from typing import Dict, Any, Optional, List
import httpx
from app.models.enums import SocialPlatform
from app.integrations.base import BasePlatformAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class FacebookAdapter(BasePlatformAdapter):
    platform = SocialPlatform.FACEBOOK

    @property
    def api_version(self) -> str:
        return settings.META_API_VERSION

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = settings.META_CLIENT_ID or "META_CLIENT_ID_PLACEHOLDER"
        uri = redirect_uri or settings.META_REDIRECT_URI
        base_url = f"https://www.facebook.com/{self.api_version}/dialog/oauth?client_id={client_id}&redirect_uri={uri}&state={state}&response_type=code&auth_type=rerequest"
        if settings.META_CONFIG_ID and settings.META_CONFIG_ID.strip():
            return f"{base_url}&config_id={settings.META_CONFIG_ID.strip()}&override_default_response_type=true"
        scope = getattr(settings, "FACEBOOK_OAUTH_SCOPES", settings.META_OAUTH_SCOPES)
        return f"{base_url}&scope={scope}"

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta Client ID and Client Secret must be configured in backend/.env")

        uri = redirect_uri or settings.META_REDIRECT_URI
        token_url = f"https://graph.facebook.com/{self.api_version}/oauth/access_token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": uri,
            "code": code,
        }
        with httpx.Client(timeout=15.0) as client:
            try:
                resp = client.get(token_url, params=params)
                data = resp.json()
            except httpx.TimeoutException:
                raise ValueError("Connection to Meta OAuth server timed out. Please try again.")
            except Exception as e:
                raise ValueError(f"Network error communicating with Meta: {e}")

            if resp.status_code != 200 or "error" in data:
                err_data = data.get("error", {})
                err_msg = err_data.get("message", "Meta OAuth token exchange failed.")
                err_code = err_data.get("code")
                logger.warning(f"Meta token exchange error [code {err_code}]: {err_msg}")
                raise ValueError(f"Meta API error: {err_msg}")

            return data

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        client_id = settings.META_CLIENT_ID
        client_secret = settings.META_CLIENT_SECRET
        if not client_id or not client_secret:
            raise ValueError("Meta Client ID and Client Secret must be configured in backend/.env")

        url = f"https://graph.facebook.com/{self.api_version}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": refresh_token,
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        url = f"https://graph.facebook.com/{self.api_version}/me"
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

    def get_user_pages(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch Facebook Pages managed by the authenticated Meta user,
        including their associated Instagram Professional/Business accounts.
        """
        url = f"https://graph.facebook.com/{self.api_version}/me/accounts"
        params = {
            "fields": "id,name,access_token,category,picture{url},instagram_business_account{id,username,name,profile_picture_url}",
            "access_token": access_token
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params)
                data = resp.json()
        except httpx.TimeoutException:
            raise ValueError("Request to Meta Graph API timed out while fetching Facebook Pages.")
        except Exception as e:
            raise ValueError(f"Network error while fetching Facebook Pages: {e}")

        if resp.status_code != 200 or "error" in data:
            err_data = data.get("error", {})
            err_msg = err_data.get("message", "Failed to retrieve Facebook Pages.")
            err_code = err_data.get("code")
            if err_code == 190:
                raise ValueError("Meta access token is expired or invalid. Please re-authenticate.")
            raise ValueError(f"Meta API error: {err_msg}")

        raw_pages = data.get("data", [])
        pages = []
        for item in raw_pages:
            page_id = str(item.get("id"))
            ig_raw = item.get("instagram_business_account")
            ig_account = None
            if ig_raw and isinstance(ig_raw, dict) and ig_raw.get("id"):
                ig_account = {
                    "id": str(ig_raw.get("id")),
                    "username": ig_raw.get("username"),
                    "name": ig_raw.get("name"),
                    "profile_picture_url": ig_raw.get("profile_picture_url"),
                }

            pages.append({
                "page_id": page_id,
                "name": item.get("name", "Facebook Page"),
                "category": item.get("category"),
                "picture_url": item.get("picture", {}).get("data", {}).get("url"),
                "page_access_token": item.get("access_token"),
                "instagram_account": ig_account,
            })
        return pages

    def get_page_instagram_account(self, page_id: str, page_access_token: str) -> Optional[Dict[str, Any]]:
        """
        Check if an Instagram Professional/Business account is connected to a specific Facebook Page.
        """
        url = f"https://graph.facebook.com/{self.api_version}/{page_id}"
        params = {
            "fields": "instagram_business_account{id,username,name,profile_picture_url}",
            "access_token": page_access_token
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    ig_raw = data.get("instagram_business_account")
                    if ig_raw and isinstance(ig_raw, dict) and ig_raw.get("id"):
                        return {
                            "id": str(ig_raw.get("id")),
                            "username": ig_raw.get("username"),
                            "name": ig_raw.get("name"),
                            "profile_picture_url": ig_raw.get("profile_picture_url"),
                        }
        except Exception as e:
            logger.warning(f"Error checking linked Instagram account for page {page_id}: {e}")
        return None

    def synchronize_account_data(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}"
            params = {
                "fields": "id,name,username,about,picture{url},category,fan_count,followers_count,instagram_business_account{id,username,name}",
                "access_token": access_token
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                data = resp.json()

            if resp.status_code != 200 or "error" in data:
                err = data.get("error", {})
                err_code = err.get("code")
                err_subcode = err.get("error_subcode")
                err_msg = err.get("message", "Facebook synchronization failed")
                is_expired = err_code == 190 or err_subcode in (463, 467)
                is_revoked = err_subcode == 458 or "revoked" in err_msg.lower() or "session has been invalidated" in err_msg.lower()
                logger.warning(f"Facebook sync failed for {account_identifier}: code={err_code}, subcode={err_subcode}, msg={err_msg}")
                return {
                    "platform": self.platform.value,
                    "account_identifier": account_identifier,
                    "status": "error",
                    "is_token_expired": is_expired,
                    "is_revoked": is_revoked,
                    "message": f"Access revoked: {err_msg}" if is_revoked else (f"Token expired or unauthorized: {err_msg}" if is_expired else err_msg)
                }

            followers = data.get("followers_count") or data.get("fan_count", 0)
            return {
                "platform": self.platform.value,
                "account_identifier": data.get("id", account_identifier),
                "account_name": data.get("name", "Facebook Page"),
                "username": data.get("username"),
                "biography": data.get("about"),
                "avatar_url": data.get("picture", {}).get("data", {}).get("url"),
                "category": data.get("category"),
                "follower_count": int(followers) if followers else 0,
                "status": "synchronized",
                "scopes": ["public_profile", "pages_show_list", "pages_read_engagement", "pages_manage_posts"],
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
            url = f"https://graph.facebook.com/{self.api_version}/me/permissions"
            params = {"access_token": access_token}
            with httpx.Client(timeout=5.0) as client:
                resp = client.delete(url, params=params)
                return resp.status_code == 200
        except Exception:
            return True

    def fetch_account_metrics(self, access_token: str, account_identifier: str) -> Dict[str, Any]:
        """Fetch Facebook Page fan/follower count via Meta Graph API."""
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}"
            params = {"fields": "followers_count,fan_count", "access_token": access_token}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    followers = data.get("followers_count") or data.get("fan_count", 0)
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "follower_count": int(followers),
                        "following_count": 0,
                        "post_count": 0,
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": "Facebook follower metrics could not be retrieved."
            }
        except Exception as e:
            logger.warning(f"Facebook fetch_account_metrics error: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "follower_count": 0, "following_count": 0, "post_count": 0,
                "notice": str(e)
            }

    def fetch_post_metrics(self, access_token: str, external_post_id: str) -> Dict[str, Any]:
        """Fetch Facebook post reactions and comments via Meta Graph API."""
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{external_post_id}"
            params = {
                "fields": "reactions.summary(total_count),comments.summary(total_count),shares",
                "access_token": access_token
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
                    comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares = data.get("shares", {}).get("count", 0)
                    total_eng = reactions + comments + shares
                    return {
                        "supported": True,
                        "platform": self.platform.value,
                        "likes": reactions,
                        "comments": comments,
                        "shares": shares,
                        "clicks": 0,
                        "views": 0,
                        "impressions": None,
                        "reach": None,
                        "engagement_rate": None,
                    }
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": f"Facebook post {external_post_id} statistics not found."
            }
        except Exception as e:
            logger.warning(f"Facebook fetch_post_metrics error for {external_post_id}: {e}")
            return {
                "supported": False,
                "platform": self.platform.value,
                "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                "views": 0, "impressions": 0, "reach": 0, "engagement_rate": 0.0,
                "notice": str(e)
            }
    def fetch_recent_posts(self, access_token: str, account_identifier: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch recent published posts from Facebook Page via Meta Graph API with pagination support.
        """
        posts = []
        max_posts = min(limit, 50)
        url = f"https://graph.facebook.com/{self.api_version}/{account_identifier}/posts"
        params = {
            "fields": "id,message,created_time,permalink_url,attachments{media_type,url,unshimmed_url,subattachments},shares,reactions.summary(total_count),comments.summary(total_count)",
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
                        reactions = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
                        comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
                        shares = item.get("shares", {}).get("count", 0)
                        total_eng = reactions + comments + shares

                        # Extract media attachment info
                        attachments = item.get("attachments", {}).get("data", [])
                        thumb = None
                        media_type = "status"
                        if attachments:
                            att = attachments[0]
                            media_type = att.get("media_type", "photo")
                            thumb = att.get("unshimmed_url") or att.get("url")

                        posts.append({
                            "external_post_id": str(item.get("id")),
                            "platform": self.platform.value,
                            "caption": item.get("message", ""),
                            "created_time": item.get("created_time"),
                            "permalink": item.get("permalink_url"),
                            "media_type": media_type,
                            "thumbnail_url": thumb,
                            "likes": reactions,
                            "comments": comments,
                            "shares": shares,
                            "impressions": None,
                            "reach": None,
                            "engagement": total_eng,
                            "engagement_rate": None,
                        })

                        if len(posts) >= max_posts:
                            break

                    # Check next page URL
                    paging = data.get("paging", {})
                    url = paging.get("next")
                    params = None
                except Exception as e:
                    logger.warning(f"Error fetching Facebook posts for {account_identifier}: {e}")
                    break

        return posts
