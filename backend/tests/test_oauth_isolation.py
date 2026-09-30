import uuid
import secrets
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, encrypt_token
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.social_account import SocialAccount
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus
from app.schemas.social_account import SocialAccountCreate
from app.services import social_account_service
from app.api.v1.oauth import (
    _save_oauth_state,
    _retrieve_and_delete_oauth_state,
    _save_oauth_session,
    _get_oauth_session,
    _IN_MEMORY_STATE_CACHE,
    _IN_MEMORY_SESSION_CACHE,
)


async def create_isolated_state(user_id: int, team_id: int, provider: str = "facebook", ttl_seconds: int = 600) -> str:
    state_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    payload = {
        "state": state_token,
        "nonce": secrets.token_hex(16),
        "user_id": user_id,
        "team_id": team_id,
        "provider": provider,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
    }
    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        await _save_oauth_state(state_token, payload)
    return state_token


@pytest.fixture
def isolation_fixture():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User A (Content Creator - Owner of Team A)
    user_a = User(
        email=f"iso_user_a_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="User A Isolated",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    # User B (Content Creator - Owner of Team B)
    user_b = User(
        email=f"iso_user_b_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="User B Isolated",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add_all([user_a, user_b])
    session.commit()

    # Team A & Team B
    team_a = Team(name=f"Team A {uid}", owner_id=user_a.id)
    team_b = Team(name=f"Team B {uid}", owner_id=user_b.id)
    session.add_all([team_a, team_b])
    session.commit()

    memb_a = TeamMember(team_id=team_a.id, user_id=user_a.id, role=UserRole.ADMINISTRATOR)
    memb_b = TeamMember(team_id=team_b.id, user_id=user_b.id, role=UserRole.ADMINISTRATOR)
    session.add_all([memb_a, memb_b])
    session.commit()

    token_a = create_access_token(subject=user_a.id)
    token_b = create_access_token(subject=user_b.id)

    # SocialAccount for User A
    account_a = SocialAccount(
        user_id=user_a.id,
        team_id=team_a.id,
        platform=SocialPlatform.FACEBOOK,
        account_identifier=f"fb_page_a_{uid}",
        account_name="User A Facebook Page",
        access_token=encrypt_token("EAAB_test_token_secret_a"),
        connection_status=SocialAccountStatus.CONNECTED,
        platform_permissions={"follower_count": 1500}
    )
    session.add(account_a)
    session.commit()

    yield {
        "user_a": user_a,
        "token_a": token_a,
        "team_a": team_a,
        "account_a": account_a,
        "user_b": user_b,
        "token_b": token_b,
        "team_b": team_b,
        "session": session,
        "uid": uid,
    }

    # Cleanup
    session.query(SocialAccount).filter(SocialAccount.user_id.in_([user_a.id, user_b.id])).delete(synchronize_session=False)
    session.query(TeamMember).filter(TeamMember.user_id.in_([user_a.id, user_b.id])).delete(synchronize_session=False)
    session.query(Team).filter(Team.owner_id.in_([user_a.id, user_b.id])).delete(synchronize_session=False)
    session.query(User).filter(User.id.in_([user_a.id, user_b.id])).delete(synchronize_session=False)
    session.commit()
    session.close()
    engine.dispose()


# TEST 1: User A starts OAuth. User B starts OAuth. Both states are different.
@pytest.mark.asyncio
async def test_1_user_a_and_b_oauth_states_are_different(isolation_fixture):
    orig_id = settings.META_CLIENT_ID
    orig_sec = settings.META_CLIENT_SECRET
    settings.META_CLIENT_ID = "test_meta_app_id"
    settings.META_CLIENT_SECRET = "test_meta_app_secret"

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            res_a = await client.get(
                f"/api/v1/oauth/facebook/authorize?team_id={isolation_fixture['team_a'].id}",
                headers={"Authorization": f"Bearer {isolation_fixture['token_a']}"}
            )
            res_b = await client.get(
                f"/api/v1/oauth/facebook/authorize?team_id={isolation_fixture['team_b'].id}",
                headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
            )

            assert res_a.status_code == 200
            assert res_b.status_code == 200

            state_a = res_a.json()["state"]
            state_b = res_b.json()["state"]

            assert state_a != state_b
            assert len(state_a) >= 32
            assert len(state_b) >= 32
            assert state_a in res_a.json()["authorization_url"]
            assert state_b in res_b.json()["authorization_url"]
    finally:
        settings.META_CLIENT_ID = orig_id
        settings.META_CLIENT_SECRET = orig_sec


# TEST 2: User A's state cannot be used by User B.
@pytest.mark.asyncio
async def test_2_user_a_state_cannot_be_used_by_user_b(isolation_fixture):
    state_a = await create_isolated_state(
        user_id=isolation_fixture["user_a"].id,
        team_id=isolation_fixture["team_a"].id,
        provider="facebook"
    )

    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        retrieved = await _retrieve_and_delete_oauth_state(state_a)
    assert retrieved is not None
    # Verify authoritative server-side ownership belongs strictly to User A and Team A
    assert retrieved["user_id"] == isolation_fixture["user_a"].id
    assert retrieved["team_id"] == isolation_fixture["team_a"].id
    assert retrieved["user_id"] != isolation_fixture["user_b"].id
    assert retrieved["team_id"] != isolation_fixture["team_b"].id


# TEST 3: User B cannot access User A's page-selection session.
@pytest.mark.asyncio
async def test_3_user_b_cannot_access_user_a_page_selection_session(isolation_fixture):
    session_token_a = f"page_session_{uuid.uuid4().hex}"
    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        await _save_oauth_session(session_token_a, {
            "user_id": isolation_fixture["user_a"].id,
            "team_id": isolation_fixture["team_a"].id,
            "provider": "facebook",
            "user_access_token": "mock_token",
            "pages": [{"id": "page_123", "name": "User A Page"}],
        })

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # User B attempts to access A's pages
        with patch("app.api.v1.oauth.get_redis_client", return_value=None):
            res = await client.get(
                f"/api/v1/oauth/facebook/pages?session_token={session_token_a}",
                headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
            )
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()


# TEST 4: User B cannot connect a page using User A's session token.
@pytest.mark.asyncio
async def test_4_user_b_cannot_connect_page_using_user_a_session_token(isolation_fixture):
    session_token_a = f"page_session_{uuid.uuid4().hex}"
    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        await _save_oauth_session(session_token_a, {
            "user_id": isolation_fixture["user_a"].id,
            "team_id": isolation_fixture["team_a"].id,
            "provider": "facebook",
            "user_access_token": "mock_token",
            "pages": [{"id": "page_456", "name": "A Secret Page", "access_token": "secret_token"}],
        })

    payload = {
        "session_token": session_token_a,
        "page_id": "page_456",
        "team_id": isolation_fixture["team_b"].id
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.oauth.get_redis_client", return_value=None):
            res = await client.post(
                "/api/v1/oauth/facebook/connect-page",
                json=payload,
                headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
            )
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()


# TEST 5: User B cannot GET User A's account.
@pytest.mark.asyncio
async def test_5_user_b_cannot_get_user_a_account(isolation_fixture):
    account_a = isolation_fixture["account_a"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/accounts/{account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# TEST 6: User B cannot POST sync on User A's account.
@pytest.mark.asyncio
async def test_6_user_b_cannot_sync_user_a_account(isolation_fixture):
    account_a = isolation_fixture["account_a"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/accounts/{account_a.id}/sync",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# TEST 7: User B cannot DELETE User A's account.
@pytest.mark.asyncio
async def test_7_user_b_cannot_delete_user_a_account(isolation_fixture):
    account_a = isolation_fixture["account_a"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.delete(
            f"/api/v1/accounts/{account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# TEST 8: User B cannot access User A's analytics.
@pytest.mark.asyncio
async def test_8_user_b_cannot_access_user_a_analytics(isolation_fixture):
    account_a = isolation_fixture["account_a"]
    team_b_id = isolation_fixture["team_b"].id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Overview with foreign account_id
        res_ov = await client.get(
            f"/api/v1/analytics/overview?team_id={team_b_id}&account_id={account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res_ov.status_code == 404

        # 2. Engagement with foreign account_id
        res_eng = await client.get(
            f"/api/v1/analytics/engagement?team_id={team_b_id}&account_id={account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res_eng.status_code == 404

        # 3. Audience with foreign account_id
        res_aud = await client.get(
            f"/api/v1/analytics/audience?team_id={team_b_id}&account_id={account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res_aud.status_code == 404

        # 4. Post performance with foreign account_id
        res_perf = await client.get(
            f"/api/v1/analytics/posts/performance?team_id={team_b_id}&account_id={account_a.id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res_perf.status_code == 404


# TEST 9: Analytics aggregation never crosses team boundaries.
@pytest.mark.asyncio
async def test_9_analytics_aggregation_never_crosses_team_boundaries(isolation_fixture):
    team_b_id = isolation_fixture["team_b"].id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/analytics/overview?team_id={team_b_id}",
            headers={"Authorization": f"Bearer {isolation_fixture['token_b']}"}
        )
        assert res.status_code == 200
        data = res.json()

        # Team B has 0 accounts connected, must not count Team A's 1 account
        assert data["accounts"]["total"] == 0
        assert data["accounts"]["connected"] == 0


# TEST 10: Background sync never writes metrics to another team's account.
@pytest.mark.asyncio
async def test_10_background_sync_never_writes_to_other_team_account(isolation_fixture):
    from app.services.analytics_ingestion_service import AnalyticsIngestionService
    account_a = isolation_fixture["account_a"]

    mock_mongo = MagicMock()
    mock_coll = MagicMock()
    mock_mongo.__getitem__.return_value = mock_coll

    with patch("app.services.analytics_ingestion_service.get_platform_adapter") as mock_adapter_getter:
        mock_adapter = MagicMock()
        mock_adapter.fetch_account_metrics.return_value = {
            "supported": True,
            "follower_count": 9999,
            "following_count": 100,
            "post_count": 50,
        }
        mock_adapter.fetch_recent_posts.return_value = []
        mock_adapter_getter.return_value = mock_adapter

        db = isolation_fixture["session"]
        res = await AnalyticsIngestionService.sync_account_analytics(db, mock_mongo, account_a)

        assert res["status"] == "success"
        # Check all upsert calls passed account_a's team_id and account_id
        for call in mock_coll.update_one.call_args_list:
            doc = call[0][1].get("$set", {})
            if "team_id" in doc:
                assert doc["team_id"] == account_a.team_id
                assert doc["team_id"] != isolation_fixture["team_b"].id
            if "account_id" in doc:
                assert doc["account_id"] == account_a.id


# TEST 11: Expired OAuth state is rejected.
@pytest.mark.asyncio
async def test_11_expired_oauth_state_is_rejected():
    state_token = f"expired_state_{uuid.uuid4().hex}"
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    # Save with already expired time
    _IN_MEMORY_STATE_CACHE[state_token] = {
        "user_id": 999,
        "team_id": 888,
        "provider": "facebook",
        "created_at": past_time,
        "expires_at": past_time
    }

    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        result = await _retrieve_and_delete_oauth_state(state_token)
    assert result is None
    assert state_token not in _IN_MEMORY_STATE_CACHE


# TEST 12: OAuth state can only be consumed once.
@pytest.mark.asyncio
async def test_12_oauth_state_can_only_be_consumed_once():
    state = await create_isolated_state(user_id=1, team_id=2, provider="facebook")

    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        # First retrieval succeeds
        first = await _retrieve_and_delete_oauth_state(state)
        assert first is not None
        assert first["user_id"] == 1
        assert first["team_id"] == 2

        # Second retrieval immediately returns None
        second = await _retrieve_and_delete_oauth_state(state)
        assert second is None


# TEST 13: Reconnect cannot silently transfer account ownership.
def test_13_reconnect_cannot_silently_transfer_ownership(isolation_fixture):
    db = isolation_fixture["session"]
    user_b = isolation_fixture["user_b"]
    team_b = isolation_fixture["team_b"]
    account_a = isolation_fixture["account_a"]

    # User B tries to connect an account with the SAME account_identifier as User A's account
    account_in = SocialAccountCreate(
        platform=account_a.platform,
        account_identifier=account_a.account_identifier,
        account_name="Hijacked Name",
        access_token="new_raw_token",
        team_id=team_b.id
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        social_account_service.connect_account(db, user_b, account_in)

    assert exc_info.value.status_code == 409
    assert "already connected to another team workspace" in exc_info.value.detail

    # Verify database still reflects team_a ownership
    db.refresh(account_a)
    assert account_a.team_id == isolation_fixture["team_a"].id
    assert account_a.user_id == isolation_fixture["user_a"].id


# TEST 14: Raw access tokens never appear in API responses.
@pytest.mark.asyncio
async def test_14_raw_access_tokens_never_appear_in_api_responses(isolation_fixture):
    token_a = isolation_fixture["token_a"]
    account_a = isolation_fixture["account_a"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. List accounts
        res_list = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token_a}"})
        assert res_list.status_code == 200
        text_list = res_list.text
        assert "EAAB_test_token_secret_a" not in text_list
        for acc in res_list.json():
            assert "access_token" not in acc

        # 2. Get single account
        res_get = await client.get(f"/api/v1/accounts/{account_a.id}", headers={"Authorization": f"Bearer {token_a}"})
        assert res_get.status_code == 200
        text_get = res_get.text
        assert "EAAB_test_token_secret_a" not in text_get
        assert "access_token" not in res_get.json()

        # 3. Status endpoint
        res_status = await client.get(f"/api/v1/accounts/{account_a.id}/status", headers={"Authorization": f"Bearer {token_a}"})
        assert res_status.status_code == 200
        text_status = res_status.text
        assert "EAAB_test_token_secret_a" not in text_status
        assert "access_token" not in res_status.json()


# TEST 15: Concurrent OAuth attempts from multiple users remain isolated.
@pytest.mark.asyncio
async def test_15_concurrent_oauth_attempts_remain_isolated():
    saved_states = {}
    with patch("app.api.v1.oauth.get_redis_client", return_value=None):
        for i in range(10):
            uid = 1000 + i
            tid = 2000 + i
            state = await create_isolated_state(user_id=uid, team_id=tid, provider="facebook")
            saved_states[state] = (uid, tid)

        # Verify all 10 states are mutually unique
        assert len(saved_states) == 10

        # Verify each state resolves back to exactly its own user and team
        for state, (expected_uid, expected_tid) in saved_states.items():
            retrieved = await _retrieve_and_delete_oauth_state(state)
            assert retrieved is not None
            assert retrieved["user_id"] == expected_uid
            assert retrieved["team_id"] == expected_tid

        # Verify all states are now fully deleted
        for state in saved_states.keys():
            assert await _retrieve_and_delete_oauth_state(state) is None
