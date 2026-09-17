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
            assert "instagram.com" in data["authorization_url"]
            assert "test_meta_client_id_123" in data["authorization_url"]
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
    mock_profile_resp = {"account_identifier": "fb_page_999", "account_name": "Test FB Page"}

    with patch("app.integrations.facebook.FacebookAdapter.exchange_code_for_token", return_value=mock_token_resp), \
         patch("app.integrations.facebook.FacebookAdapter.get_user_profile", return_value=mock_profile_resp):

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/oauth/facebook/callback?code=mock_code_123&state={state_token}"
            )
            assert resp.status_code == 307
            assert "status=success" in resp.headers["location"]
            assert "platform=facebook" in resp.headers["location"]

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
    user_id = test_user["user_id"]
    state_token = f"valid_ig_state_{uuid.uuid4().hex[:6]}"
    await _save_oauth_state(state_token, {
        "user_id": user_id,
        "team_id": None,
        "provider": "instagram",
        "created_at": "2026-09-03T12:00:00Z"
    })

    mock_token_resp = {"access_token": "mock_ig_access_token_888", "expires_in": 3600}
    mock_profile_resp = {"account_identifier": "ig_user_555", "account_name": "Test Instagram Account"}

    with patch("app.integrations.instagram.InstagramAdapter.exchange_code_for_token", return_value=mock_token_resp), \
         patch("app.integrations.instagram.InstagramAdapter.get_user_profile", return_value=mock_profile_resp):

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/oauth/instagram/callback?code=mock_code_456&state={state_token}"
            )
            assert resp.status_code == 307
            assert "status=success" in resp.headers["location"]
            assert "platform=instagram" in resp.headers["location"]

            # Verify SocialAccount record created in DB
            session = test_user["session"]
            acc = session.query(SocialAccount).filter_by(
                user_id=user_id,
                platform=SocialPlatform.INSTAGRAM,
                account_identifier="ig_user_555"
            ).first()
            assert acc is not None
            assert acc.account_name == "Test Instagram Account"


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
