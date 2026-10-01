import uuid
import pytest
import httpx
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.enums import UserRole, SocialPlatform
from app.models.social_account import SocialAccount
from app.api.v1.oauth import _save_oauth_state


@pytest.fixture
def test_user():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(
        email=f"meta_tester_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Meta Tester",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add(user)
    session.commit()
    token = create_access_token(subject=user.id)
    user_id = user.id

    yield {"user": user, "user_id": user_id, "token": token, "session": session}

    session.query(SocialAccount).filter_by(user_id=user_id).delete()
    session.query(User).filter_by(id=user_id).delete()
    session.commit()
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_meta_config_missing_handling(test_user):
    token = test_user["token"]
    original_id = settings.META_CLIENT_ID
    settings.META_CLIENT_ID = None

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp_fb = await client.get(
                "/api/v1/oauth/facebook/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp_fb.status_code == 400
            assert "Instagram/Meta OAuth is not configured" in resp_fb.json()["detail"]

            resp_ig = await client.get(
                "/api/v1/oauth/instagram/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp_ig.status_code == 400
            assert "Instagram/Meta OAuth is not configured" in resp_ig.json()["detail"]
    finally:
        settings.META_CLIENT_ID = original_id


@pytest.mark.asyncio
async def test_facebook_authorization_endpoint(test_user):
    token = test_user["token"]
    original_id = settings.META_CLIENT_ID
    original_secret = settings.META_CLIENT_SECRET
    settings.META_CLIENT_ID = "test_meta_client_id_123"
    settings.META_CLIENT_SECRET = "test_meta_client_secret_456"

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/facebook/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "authorization_url" in data
            assert "state" in data
            assert "facebook.com" in data["authorization_url"]
            assert "test_meta_client_id_123" in data["authorization_url"]
            # Verify clean Facebook Page scopes (no Instagram scopes)
            assert "pages_show_list" in data["authorization_url"]
            assert "instagram_basic" not in data["authorization_url"]
    finally:
        settings.META_CLIENT_ID = original_id
        settings.META_CLIENT_SECRET = original_secret


@pytest.mark.asyncio
async def test_instagram_authorization_endpoint(test_user):
    token = test_user["token"]
    original_id = settings.META_CLIENT_ID
    original_secret = settings.META_CLIENT_SECRET
    settings.META_CLIENT_ID = "test_meta_client_id_123"
    settings.META_CLIENT_SECRET = "test_meta_client_secret_456"

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/instagram/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "authorization_url" in data
            assert "state" in data
            # Instagram uses dedicated Instagram Login dialog
            assert "instagram.com" in data["authorization_url"]
            assert "test_meta_client_id_123" in data["authorization_url"]
            # Verify modern Instagram Business scopes (no Facebook Page scopes)
            assert "instagram_business_basic" in data["authorization_url"]
            assert "pages_show_list" not in data["authorization_url"]
    finally:
        settings.META_CLIENT_ID = original_id
        settings.META_CLIENT_SECRET = original_secret


@pytest.mark.asyncio
async def test_facebook_callback_success_account_creation(test_user):
    user_id = test_user["user_id"]
    state_token = f"valid_fb_state_{uuid.uuid4().hex[:6]}"
    await _save_oauth_state(state_token, {
        "user_id": user_id,
        "team_id": None,
        "provider": "facebook",
        "created_at": "2026-09-03T12:00:00Z"
    })

    mock_token_resp = {"access_token": "mock_fb_access_token_777", "expires_in": 3600}
    mock_pages_resp = [
        {
            "page_id": "fb_page_999",
            "name": "Test FB Page",
            "category": "Brand",
            "picture_url": "https://example.com/avatar.jpg",
            "page_access_token": "mock_page_token_123",
            "instagram_account": None
        }
    ]

    with patch("app.integrations.facebook.FacebookAdapter.exchange_code_for_token", return_value=mock_token_resp), \
         patch("app.integrations.facebook.FacebookAdapter.get_user_pages", return_value=mock_pages_resp):

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/oauth/facebook/callback?code=mock_code_123&state={state_token}"
            )
            assert resp.status_code == 307
            loc = resp.headers["location"]
            assert "status=select_pages" in loc
            assert "session_token=" in loc

            # Extract session token
            session_token = loc.split("session_token=")[1].split("&")[0]

            # Fetch available pages
            token = test_user["token"]
            pages_resp = await client.get(
                f"/api/v1/oauth/facebook/pages?session_token={session_token}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert pages_resp.status_code == 200
            pages_data = pages_resp.json()
            assert len(pages_data["pages"]) == 1
            assert pages_data["pages"][0]["page_id"] == "fb_page_999"

            # Connect the selected page
            connect_resp = await client.post(
                "/api/v1/oauth/facebook/connect-page",
                json={
                    "session_token": session_token,
                    "page_id": "fb_page_999",
                    "connect_instagram": False
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert connect_resp.status_code == 200
            connect_data = connect_resp.json()
            assert connect_data["status"] == "success"
            assert connect_data["facebook_account"]["account_identifier"] == "fb_page_999"

            # Verify SocialAccount record created in DB
            session = test_user["session"]
            acc = session.query(SocialAccount).filter_by(
                user_id=user_id,
                platform=SocialPlatform.FACEBOOK,
                account_identifier="fb_page_999"
            ).first()
            assert acc is not None
            assert acc.account_name == "Test FB Page"


@pytest.mark.asyncio
async def test_instagram_callback_success_account_creation(test_user):
    """
    Direct Instagram OAuth flow:
    Connect Instagram → /oauth/instagram/callback → saves Instagram account → redirects with success.
    """
    user_id = test_user["user_id"]
    state_token = f"valid_ig_state_{uuid.uuid4().hex[:6]}"
    await _save_oauth_state(state_token, {
        "user_id": user_id,
        "team_id": None,
        "provider": "instagram",
        "created_at": "2026-09-03T12:00:00Z"
    })

    mock_token_resp = {"access_token": "mock_ig_access_token_888", "expires_in": 5184000, "user_id": "1784140099"}
    mock_profile_resp = {
        "account_identifier": "1784140099",
        "account_name": "testinstagram",
        "username": "testinstagram",
        "name": "Test Instagram Account",
        "avatar_url": "https://example.com/avatar_ig.jpg",
        "followers_count": 4500,
        "follows_count": 210,
        "media_count": 34,
        "account_type": "BUSINESS"
    }

    with patch("app.integrations.instagram.InstagramAdapter.exchange_code_for_token", return_value=mock_token_resp), \
         patch("app.integrations.instagram.InstagramAdapter.get_user_profile", return_value=mock_profile_resp), \
         patch("app.integrations.instagram.InstagramAdapter.synchronize_account_data", return_value={
             "platform": "instagram",
             "account_identifier": "1784140099",
             "status": "synchronized",
             "follower_count": 4500,
             "following_count": 210,
             "post_count": 34
         }):

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/oauth/instagram/callback?code=mock_code_ig_456&state={state_token}"
            )
            assert resp.status_code == 307
            loc = resp.headers["location"]
            assert "status=success" in loc
            assert "platform=instagram" in loc
            assert "testinstagram" in loc

            # Verify SocialAccount record created in DB with platform = INSTAGRAM
            session = test_user["session"]
            acc = session.query(SocialAccount).filter_by(
                user_id=user_id,
                platform=SocialPlatform.INSTAGRAM,
                account_identifier="1784140099"
            ).first()
            assert acc is not None
            assert acc.account_name == "testinstagram"
            assert acc.platform == SocialPlatform.INSTAGRAM


@pytest.mark.asyncio
async def test_invalid_oauth_state_rejection():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/facebook/callback?code=some_code&state=bogus_state_xyz"
        )
        assert resp.status_code == 307
        assert "status=error" in resp.headers["location"]
        assert "Invalid" in resp.headers["location"] or "state" in resp.headers["location"]


@pytest.mark.asyncio
async def test_token_exchange_failure_handling(test_user):
    user_id = test_user["user_id"]
    state_token = f"err_fb_state_{uuid.uuid4().hex[:6]}"
    await _save_oauth_state(state_token, {
        "user_id": user_id,
        "team_id": None,
        "provider": "facebook",
        "created_at": "2026-09-03T12:00:00Z"
    })

    with patch("app.integrations.facebook.FacebookAdapter.exchange_code_for_token", side_effect=ValueError("Meta API returned HTTP 400 Bad Request")):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/oauth/facebook/callback?code=bad_code_789&state={state_token}"
            )
            assert resp.status_code == 307
            assert "status=error" in resp.headers["location"]
            assert "Failed" in resp.headers["location"] or "Bad Request" in resp.headers["location"]
