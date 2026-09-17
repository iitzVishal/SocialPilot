import uuid
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.enums import UserRole


@pytest.fixture
def test_user_token():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(
        email=f"oauth_tester_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="OAuth Tester",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add(user)
    session.commit()
    token = create_access_token(subject=user.id)
    user_id = user.id

    yield {"user_id": user_id, "token": token, "session": session}

    session.query(User).filter_by(id=user_id).delete()
    session.commit()
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_oauth_unsupported_provider(test_user_token):
    token = test_user_token["token"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/invalid_provider/authorize",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400
        assert "Unsupported OAuth provider" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_missing_credentials_handling(test_user_token):
    token = test_user_token["token"]
    # Ensure client ID is None to test missing creds handling
    original_id = settings.META_CLIENT_ID
    settings.META_CLIENT_ID = None
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/facebook/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 400
            assert "not configured" in resp.json()["detail"]
    finally:
        settings.META_CLIENT_ID = original_id


@pytest.mark.asyncio
async def test_oauth_authorization_url_generation(test_user_token):
    token = test_user_token["token"]
    settings.META_CLIENT_ID = "test_meta_app_123"
    settings.META_CLIENT_SECRET = "test_meta_secret_456"

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
        assert "test_meta_app_123" in data["authorization_url"]
        assert data["state"] in data["authorization_url"]


@pytest.mark.asyncio
async def test_oauth_callback_user_denied():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/facebook/callback?error=access_denied&error_description=Permissions+denied"
        )
        assert resp.status_code == 307
        assert "status=error" in resp.headers["location"]
        assert "Permissions" in resp.headers["location"] or "denied" in resp.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/facebook/callback?code=fake_code_123&state=invalid_bogus_state"
        )
        assert resp.status_code == 307
        assert "status=error" in resp.headers["location"]
        assert "Invalid" in resp.headers["location"] or "state" in resp.headers["location"]
