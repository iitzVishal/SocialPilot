import uuid
from datetime import datetime, timedelta, timezone
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, decrypt_token
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus


@pytest.fixture
def test_user_and_token():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(
        email=f"acc_tester_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Account Tester",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add(user)
    session.commit()
    token = create_access_token(subject=user.id)
    user_id = user.id

    yield {"user_id": user_id, "token": token, "session": session}

    # Cleanup
    session.query(SocialAccount).filter_by(user_id=user_id).delete()
    session.query(User).filter_by(id=user_id).delete()
    session.commit()
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_connect_account_and_security(test_user_and_token):
    """1. Authenticated user can connect, 10. No raw access token, 11. No raw refresh token."""
    token = test_user_and_token["token"]
    raw_secret_access = "secret_access_token_fb_987654321"
    raw_secret_refresh = "secret_refresh_token_fb_123456789"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Connect Facebook account
        res = await client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "platform": "facebook",
                "account_identifier": "fb_page_1001",
                "account_name": "My Official Brand Page",
                "access_token": raw_secret_access,
                "refresh_token": raw_secret_refresh,
                "platform_permissions": {"publish_posts": True, "read_insights": True}
            }
        )
        assert res.status_code == 201
        data = res.json()
        assert data["platform"] == "facebook"
        assert data["account_name"] == "My Official Brand Page"
        assert data["connection_status"] == "connected"
        assert data["platform_permissions"]["publish_posts"] is True

        # 10 & 11. Verify raw tokens are NEVER exposed in the API response
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert raw_secret_access not in str(data)
        assert raw_secret_refresh not in str(data)

    # Verify that in the database, the token is encrypted
    session = test_user_and_token["session"]
    db_acc = session.query(SocialAccount).filter_by(account_identifier="fb_page_1001").first()
    assert db_acc is not None
    assert db_acc.access_token != raw_secret_access
    assert decrypt_token(db_acc.access_token) == raw_secret_access
    assert decrypt_token(db_acc.refresh_token) == raw_secret_refresh


@pytest.mark.asyncio
async def test_unauthenticated_cannot_connect():
    """2. Unauthenticated user cannot connect an account."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/accounts",
            json={
                "platform": "instagram",
                "account_identifier": "ig_user_2002",
                "account_name": "My Instagram",
                "access_token": "some_token"
            }
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_and_filters(test_user_and_token):
    """3. List accounts, 4. Platform filtering, 5. Status filtering."""
    token = test_user_and_token["token"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Create two accounts: instagram and twitter
        await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "instagram",
                "account_identifier": "ig_3001",
                "account_name": "Insta Account",
                "access_token": "token_ig"
            }
        )
        await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "twitter",
                "account_identifier": "tw_3002",
                "account_name": "Twitter Account",
                "access_token": "token_tw"
            }
        )

        # 3. List all accounts
        list_all = await client.get("/api/v1/accounts", headers=headers)
        assert list_all.status_code == 200
        assert len(list_all.json()) >= 2

        # 4. Platform filter: instagram
        filter_ig = await client.get("/api/v1/accounts?platform=instagram", headers=headers)
        assert filter_ig.status_code == 200
        ig_items = filter_ig.json()
        assert len(ig_items) == 1
        assert ig_items[0]["platform"] == "instagram"

        # 5. Status filter: connected
        filter_status = await client.get("/api/v1/accounts?connection_status=connected", headers=headers)
        assert filter_status.status_code == 200
        for item in filter_status.json():
            assert item["connection_status"] == "connected"


@pytest.mark.asyncio
async def test_get_and_ownership_isolation(test_user_and_token):
    """6. Retrieve own account, 7. User cannot retrieve another user's account."""
    token1 = test_user_and_token["token"]

    # Create second independent user
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session2 = Session()
    user2 = User(
        email=f"other_user_{uuid.uuid4().hex[:8]}@socialpilot.test",
        hashed_password="pw",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session2.add(user2)
    session2.commit()
    token2 = create_access_token(subject=user2.id)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # User 1 creates account
        create_res = await client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "platform": "linkedin",
                "account_identifier": "li_4001",
                "account_name": "User 1 LinkedIn",
                "access_token": "token_li"
            }
        )
        acc_id = create_res.json()["id"]

        # 6. User 1 retrieves own account
        get_res1 = await client.get(f"/api/v1/accounts/{acc_id}", headers={"Authorization": f"Bearer {token1}"})
        assert get_res1.status_code == 200
        assert get_res1.json()["id"] == acc_id

        # 7. User 2 attempts to retrieve User 1's account -> 404
        get_res2 = await client.get(f"/api/v1/accounts/{acc_id}", headers={"Authorization": f"Bearer {token2}"})
        assert get_res2.status_code == 404

    session2.query(User).filter_by(id=user2.id).delete()
    session2.commit()
    session2.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_disconnect_and_status(test_user_and_token):
    """8. Disconnect account, 12. Token expiration status."""
    token = test_user_and_token["token"]
    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Create account with expired token date
        create_res = await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "youtube",
                "account_identifier": "yt_5001",
                "account_name": "YouTube Channel",
                "access_token": "token_yt",
                "token_expires_at": past_date
            }
        )
        acc_id = create_res.json()["id"]

        # 12. Check status and token expiration
        status_res = await client.get(f"/api/v1/accounts/{acc_id}/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["is_token_expired"] is True
        assert status_res.json()["connection_status"] == "connected"

        # 8. Disconnect account
        disc_res = await client.delete(f"/api/v1/accounts/{acc_id}", headers=headers)
        assert disc_res.status_code == 200
        assert disc_res.json()["connection_status"] == "revoked"


@pytest.mark.asyncio
async def test_duplicate_account_handling(test_user_and_token):
    """9. Duplicate account handling safely reconnects and updates existing record."""
    token = test_user_and_token["token"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # First connection
        r1 = await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "pinterest",
                "account_identifier": "pin_6001",
                "account_name": "Pinterest Board Initial",
                "access_token": "token_pin_initial"
            }
        )
        assert r1.status_code == 201
        acc_id1 = r1.json()["id"]

        # Second connection with same platform & identifier
        r2 = await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "pinterest",
                "account_identifier": "pin_6001",
                "account_name": "Pinterest Board Updated",
                "access_token": "token_pin_updated"
            }
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == acc_id1
        assert r2.json()["account_name"] == "Pinterest Board Updated"


@pytest.mark.asyncio
async def test_all_six_platforms_accepted_and_invalid_rejected(test_user_and_token):
    """16. All six platforms accepted, 17. Invalid platform rejected."""
    token = test_user_and_token["token"]
    platforms = ["facebook", "instagram", "linkedin", "twitter", "youtube", "pinterest"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        for idx, p in enumerate(platforms):
            res = await client.post(
                "/api/v1/accounts",
                headers=headers,
                json={
                    "platform": p,
                    "account_identifier": f"id_{p}_{idx}",
                    "account_name": f"{p.capitalize()} Profile",
                    "access_token": f"token_{p}"
                }
            )
            assert res.status_code == 201
            assert res.json()["platform"] == p

        # 17. Invalid platform
        res_invalid = await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "tiktok_not_supported",
                "account_identifier": "id_invalid",
                "account_name": "Invalid Profile",
                "access_token": "token"
            }
        )
        assert res_invalid.status_code == 422


@pytest.mark.asyncio
async def test_synchronization_and_permissions(test_user_and_token):
    """13. Permissions update, 14. Sync requires auth, 15. Sync returns structured response."""
    token = test_user_and_token["token"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "platform": "facebook",
                "account_identifier": "fb_sync_7001",
                "account_name": "FB Sync Page",
                "access_token": "token_fb_sync"
            }
        )
        acc_id = create_res.json()["id"]

        # 13. Update permissions
        perm_res = await client.patch(
            f"/api/v1/accounts/{acc_id}/permissions",
            headers=headers,
            json={"platform_permissions": {"custom_scope": True, "read_all": True}}
        )
        assert perm_res.status_code == 200
        assert perm_res.json()["platform_permissions"]["custom_scope"] is True

        # 14. Sync without authentication -> 401
        no_auth_sync = await client.post(f"/api/v1/accounts/{acc_id}/sync")
        assert no_auth_sync.status_code == 401

        # 15. Trigger sync with auth -> returns structured success with explicit integration note
        sync_res = await client.post(f"/api/v1/accounts/{acc_id}/sync", headers=headers)
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["sync_status"] == "success"
        assert sync_data["account_id"] == acc_id
        assert sync_data["platform"] == "facebook"
        assert "Synchronization workflow executed" in sync_data["message"]
