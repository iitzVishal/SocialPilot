import uuid
import pytest
import httpx
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, decrypt_token
from app.models.user import User
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus
from app.models.social_account import SocialAccount
from app.api.v1.oauth import _save_oauth_state, _save_oauth_session


@pytest.fixture
def test_users():
    uid1 = uuid.uuid4().hex[:6]
    uid2 = uuid.uuid4().hex[:6]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    user1 = User(
        email=f"user_a_{uid1}@socialpilot.test",
        hashed_password="hashed_pw_test_1",
        full_name="User Alpha",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    user2 = User(
        email=f"user_b_{uid2}@socialpilot.test",
        hashed_password="hashed_pw_test_2",
        full_name="User Beta",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add(user1)
    session.add(user2)
    session.commit()

    token1 = create_access_token(subject=user1.id)
    token2 = create_access_token(subject=user2.id)

    u1_id = user1.id
    u2_id = user2.id

    yield {
        "user1": user1, "token1": token1, "u1_id": u1_id,
        "user2": user2, "token2": token2, "u2_id": u2_id,
        "session": session
    }

    session.query(SocialAccount).filter(SocialAccount.user_id.in_([u1_id, u2_id])).delete()
    session.query(User).filter(User.id.in_([u1_id, u2_id])).delete()
    session.commit()
    session.close()
    engine.dispose()


# -------------------------------------------------------------
# 1. AUTHORIZATION & OWNERSHIP ISOLATION TESTS
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Unauthenticated page list request
        resp1 = await client.get("/api/v1/oauth/facebook/pages?session_token=some_token")
        assert resp1.status_code == 401

        # Unauthenticated connect-page request
        resp2 = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={"session_token": "some_token", "page_id": "123"}
        )
        assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_oauth_session_isolation(test_users):
    token1 = test_users["token1"]
    token2 = test_users["token2"]
    user1_id = test_users["u1_id"]

    session_token = f"session_u1_{uuid.uuid4().hex[:8]}"
    await _save_oauth_session(session_token, {
        "user_id": user1_id,
        "team_id": None,
        "provider": "facebook",
        "user_access_token": "secret_user_token_123",
        "pages": [
            {
                "page_id": "fb_page_private_1",
                "name": "User 1 Secret Page",
                "category": "Private",
                "picture_url": "https://img.test/pic.png",
                "page_access_token": "secret_page_token_999",
                "instagram_account": None
            }
        ]
    })

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # User 2 attempts to access User 1's OAuth session -> 403 Forbidden
        resp_forbidden = await client.get(
            f"/api/v1/oauth/facebook/pages?session_token={session_token}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert resp_forbidden.status_code == 403
        assert "forbidden" in resp_forbidden.json()["detail"].lower()

        # User 2 attempts to connect User 1's page using session -> 403 Forbidden
        resp_connect_forbidden = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={"session_token": session_token, "page_id": "fb_page_private_1"},
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert resp_connect_forbidden.status_code == 403

        # User 1 (legitimate owner) accesses successfully
        resp_allowed = await client.get(
            f"/api/v1/oauth/facebook/pages?session_token={session_token}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert resp_allowed.status_code == 200
        data = resp_allowed.json()
        assert len(data["pages"]) == 1
        assert data["pages"][0]["page_id"] == "fb_page_private_1"


# -------------------------------------------------------------
# 2. FACEBOOK PAGE FETCH & PAGE SELECTION FLOW
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_facebook_page_selection_and_token_security(test_users):
    token1 = test_users["token1"]
    user1_id = test_users["u1_id"]

    session_token = f"session_sel_{uuid.uuid4().hex[:8]}"
    raw_page_token = "raw_super_secret_meta_page_token_xyz_888"
    await _save_oauth_session(session_token, {
        "user_id": user1_id,
        "team_id": None,
        "provider": "facebook",
        "user_access_token": "raw_user_token_abc",
        "pages": [
            {
                "page_id": "page_to_connect_1",
                "name": "SocialPilot Official Page",
                "category": "Software Company",
                "picture_url": "https://img.test/sp_page.png",
                "page_access_token": raw_page_token,
                "instagram_account": None
            },
            {
                "page_id": "page_unselected_2",
                "name": "Other Ignored Page",
                "category": "Personal Blog",
                "picture_url": None,
                "page_access_token": "other_token_456",
                "instagram_account": None
            }
        ]
    })

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Step A: Get pages - verify tokens are NOT exposed
        pages_resp = await client.get(
            f"/api/v1/oauth/facebook/pages?session_token={session_token}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert pages_resp.status_code == 200
        pages_json = pages_resp.json()
        assert len(pages_json["pages"]) == 2

        # CRITICAL SECURITY RULE: Raw page tokens must never appear in response
        raw_response_text = pages_resp.text
        assert raw_page_token not in raw_response_text
        assert "other_token_456" not in raw_response_text
        assert "access_token" not in raw_response_text

        # Step B: Connect selected page
        connect_resp = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={
                "session_token": session_token,
                "page_id": "page_to_connect_1",
                "connect_instagram": False
            },
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert connect_resp.status_code == 200
        conn_json = connect_resp.json()
        assert conn_json["status"] == "success"
        assert conn_json["facebook_account"]["account_identifier"] == "page_to_connect_1"
        assert conn_json["facebook_account"]["account_name"] == "SocialPilot Official Page"

        # Verify token in response is not raw
        assert raw_page_token not in connect_resp.text

        # Verify database record: token is AES encrypted and matches decrypted value
        session = test_users["session"]
        account = session.query(SocialAccount).filter_by(
            user_id=user1_id,
            account_identifier="page_to_connect_1"
        ).first()
        assert account is not None
        assert account.access_token != raw_page_token  # Must be encrypted!
        assert decrypt_token(account.access_token) == raw_page_token

        # Unselected page must NOT be in DB
        unselected = session.query(SocialAccount).filter_by(
            user_id=user1_id,
            account_identifier="page_unselected_2"
        ).first()
        assert unselected is None

        # Verify session token was invalidated/deleted
        pages_after = await client.get(
            f"/api/v1/oauth/facebook/pages?session_token={session_token}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert pages_after.status_code == 404


# -------------------------------------------------------------
# 3. INSTAGRAM PROFESSIONAL ACCOUNT LINKING
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_facebook_page_with_linked_instagram_connection(test_users):
    token1 = test_users["token1"]
    user1_id = test_users["u1_id"]

    session_token = f"session_ig_{uuid.uuid4().hex[:8]}"
    raw_token = "raw_page_token_with_ig_perms"
    await _save_oauth_session(session_token, {
        "user_id": user1_id,
        "team_id": None,
        "provider": "facebook",
        "user_access_token": "raw_user_token_abc",
        "pages": [
            {
                "page_id": "fb_page_brand_55",
                "name": "Fashion Brand HQ",
                "category": "Clothing",
                "picture_url": "https://img.test/brand.png",
                "page_access_token": raw_token,
                "instagram_account": {
                    "id": "17841400998877",
                    "username": "fashionbrandhq",
                    "name": "Fashion Brand Official",
                    "profile_picture_url": "https://img.test/ig_profile.png"
                }
            }
        ]
    })

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Check page retrieval has instagram info
        resp = await client.get(
            f"/api/v1/oauth/facebook/pages?session_token={session_token}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert resp.status_code == 200
        p = resp.json()["pages"][0]
        assert p["has_instagram"] is True
        assert p["instagram_account"]["username"] == "fashionbrandhq"

        # Connect both Facebook Page and linked Instagram account
        connect_resp = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={
                "session_token": session_token,
                "page_id": "fb_page_brand_55",
                "connect_instagram": True
            },
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert connect_resp.status_code == 200
        conn_data = connect_resp.json()
        assert conn_data["facebook_account"]["account_identifier"] == "fb_page_brand_55"
        assert conn_data["instagram_account"] is not None
        assert conn_data["instagram_account"]["account_identifier"] == "17841400998877"
        assert conn_data["instagram_account"]["account_name"] == "fashionbrandhq"

        # Verify both records in DB
        session = test_users["session"]
        fb_db = session.query(SocialAccount).filter_by(
            user_id=user1_id,
            platform=SocialPlatform.FACEBOOK,
            account_identifier="fb_page_brand_55"
        ).first()
        ig_db = session.query(SocialAccount).filter_by(
            user_id=user1_id,
            platform=SocialPlatform.INSTAGRAM,
            account_identifier="17841400998877"
        ).first()
        assert fb_db is not None
        assert ig_db is not None
        assert decrypt_token(ig_db.access_token) == raw_token


@pytest.mark.asyncio
async def test_facebook_page_without_instagram_requesting_instagram_fails_gracefully(test_users):
    token1 = test_users["token1"]
    user1_id = test_users["u1_id"]

    session_token = f"session_no_ig_{uuid.uuid4().hex[:8]}"
    await _save_oauth_session(session_token, {
        "user_id": user1_id,
        "team_id": None,
        "provider": "facebook",
        "user_access_token": "token_abc",
        "pages": [
            {
                "page_id": "page_standalone_1",
                "name": "Standalone Page",
                "category": "Local Business",
                "picture_url": None,
                "page_access_token": "standalone_token",
                "instagram_account": None
            }
        ]
    })

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Requesting connect_instagram on a page with NO instagram account
        connect_resp = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={
                "session_token": session_token,
                "page_id": "page_standalone_1",
                "connect_instagram": True
            },
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert connect_resp.status_code == 400
        detail = connect_resp.json()["detail"]
        assert "An Instagram Professional/Business account is not connected to this Facebook Page" in detail


# -------------------------------------------------------------
# 4. ACCOUNT LIFECYCLE: LIST, DETAIL, SYNC, DISCONNECT
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_accounts_lifecycle(test_users):
    token1 = test_users["token1"]
    token2 = test_users["token2"]
    user1_id = test_users["u1_id"]

    session_token = f"session_life_{uuid.uuid4().hex[:8]}"
    await _save_oauth_session(session_token, {
        "user_id": user1_id,
        "team_id": None,
        "provider": "facebook",
        "user_access_token": "tok_123",
        "pages": [
            {
                "page_id": "lifecycle_page_100",
                "name": "Lifecycle Page",
                "category": "Media",
                "picture_url": "https://img.test/p1.png",
                "page_access_token": "tok_page_100",
                "instagram_account": None
            }
        ]
    })

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Connect
        conn_res = await client.post(
            "/api/v1/oauth/facebook/connect-page",
            json={"session_token": session_token, "page_id": "lifecycle_page_100"},
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert conn_res.status_code == 200
        account_id = conn_res.json()["facebook_account"]["id"]

        # 2. List accounts
        list_res = await client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert list_res.status_code == 200
        accs = list_res.json()
        assert any(a["id"] == account_id for a in accs)

        # User 2 list does NOT contain User 1's account
        list_res_u2 = await client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert list_res_u2.status_code == 200
        assert not any(a["id"] == account_id for a in list_res_u2.json())

        # 3. Get single account
        detail_res = await client.get(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert detail_res.status_code == 200
        assert detail_res.json()["account_identifier"] == "lifecycle_page_100"

        # User 2 cannot access single account
        detail_res_u2 = await client.get(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert detail_res_u2.status_code == 404

        # 4. Sync account with mock adapter sync
        mock_sync_data = {
            "platform": "facebook",
            "account_identifier": "lifecycle_page_100",
            "account_name": "Lifecycle Page Updated",
            "avatar_url": "https://img.test/updated_avatar.png",
            "status": "synchronized",
            "scopes": ["public_profile", "pages_show_list"],
            "external_sync": True
        }
        with patch("app.integrations.facebook.FacebookAdapter.synchronize_account_data", return_value=mock_sync_data):
            sync_res = await client.post(
                f"/api/v1/accounts/{account_id}/sync",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert sync_res.status_code == 200
            assert sync_res.json()["sync_status"] in ("success", "synchronized")

        # 5. Expired token handling during sync
        mock_expired_sync = {
            "platform": "facebook",
            "account_identifier": "lifecycle_page_100",
            "status": "error",
            "is_token_expired": True,
            "message": "Token expired or unauthorized: Error validating access token: Session has expired."
        }
        with patch("app.integrations.facebook.FacebookAdapter.synchronize_account_data", return_value=mock_expired_sync):
            sync_expired_res = await client.post(
                f"/api/v1/accounts/{account_id}/sync",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert sync_expired_res.status_code == 200
            assert sync_expired_res.json()["connection_status"] == "expired"

        # 6. Disconnect account
        disc_res = await client.delete(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert disc_res.status_code == 200
        assert disc_res.json()["connection_status"] == "revoked"
