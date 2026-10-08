import hmac
import hashlib
import json
from datetime import datetime, timezone, date, timedelta
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.social_account import SocialAccount
from app.models.instagram_data import InstagramMetricSnapshot, InstagramMedia, InstagramComment, MetaWebhookEvent
from app.models.enums import SocialPlatform, SocialAccountStatus, UserRole
from app.core.security import encrypt_token, get_password_hash
from app.db.postgres import SessionLocal
from app.services.instagram_command_service import InstagramCommandService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def command_center_test_data(db: Session):
    """Fixture providing user, team, and connected Instagram account."""
    import uuid
    unique_email = f"ig_test_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="IG Test User",
        is_active=True,
        role=UserRole.BUSINESS_USER
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    team = Team(name="IG Growth Team", owner_id=user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    membership = TeamMember(team_id=team.id, user_id=user.id, role=UserRole.ADMINISTRATOR)
    db.add(membership)

    account = SocialAccount(
        user_id=user.id,
        team_id=team.id,
        platform=SocialPlatform.INSTAGRAM,
        account_identifier="17841400000000001",
        account_name="socialpilot_command",
        access_token=encrypt_token("EAAB_test_mock_token_12345"),
        connection_status=SocialAccountStatus.CONNECTED,
        sync_status="idle"
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    yield {"user": user, "team": team, "account": account}

    try:
        db.query(InstagramComment).filter(InstagramComment.account_id == account.id).delete()
        db.query(InstagramMedia).filter(InstagramMedia.account_id == account.id).delete()
        db.query(InstagramMetricSnapshot).filter(InstagramMetricSnapshot.account_id == account.id).delete()
        db.query(SocialAccount).filter(SocialAccount.id == account.id).delete()
        db.query(TeamMember).filter(TeamMember.team_id == team.id).delete()
        db.query(Team).filter(Team.id == team.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    except Exception:
        db.rollback()


def test_performance_score_deterministic_formula():
    """Verify the SocialPilot Performance Score formula is strictly deterministic and bounded."""
    score1 = InstagramCommandService.calculate_performance_score(
        likes=120, comments=45, shares=18, saved=32, reach=1500, follower_count=2000
    )
    score2 = InstagramCommandService.calculate_performance_score(
        likes=120, comments=45, shares=18, saved=32, reach=1500, follower_count=2000
    )
    assert score1 == score2
    assert 0.0 <= score1 <= 100.0

    # Max bound test
    huge_score = InstagramCommandService.calculate_performance_score(
        likes=100000, comments=50000, shares=25000, saved=10000, reach=500000, follower_count=100
    )
    assert huge_score == 100.0


def test_sync_instagram_account_creates_snapshots_and_media(db: Session, command_center_test_data):
    """Verify synchronization persists account metrics, historical snapshots, and media into PostgreSQL."""
    account = command_center_test_data["account"]

    mock_profile = {
        "status": "synchronized",
        "account_identifier": account.account_identifier,
        "username": "socialpilot_command",
        "follower_count": 1450,
        "following_count": 320,
        "post_count": 12,
        "avatar_url": "https://example.com/avatar.jpg"
    }

    mock_insights = {
        "impressions": 4800,
        "reach": 2100,
        "profile_views": 85,
        "website_clicks": 14,
        "supported": True
    }

    mock_recent_posts = [
        {
            "external_post_id": "999888111222",
            "caption": "Exciting Command Center Launch! #socialpilot",
            "media_type": "IMAGE",
            "permalink": "https://instagram.com/p/test1",
            "thumbnail_url": "https://example.com/thumb1.jpg",
            "created_time": "2026-10-08T10:00:00+00:00",
            "likes": 88,
            "comments": 24
        }
    ]

    mock_media_insights = {
        "reach": 950,
        "saved": 15,
        "shares": 8,
        "views": 1100,
        "supported": True
    }

    with patch("app.integrations.instagram.InstagramAdapter.synchronize_account_data", return_value=mock_profile), \
         patch("app.integrations.instagram.InstagramAdapter.fetch_account_insights", return_value=mock_insights), \
         patch("app.integrations.instagram.InstagramAdapter.fetch_recent_posts", return_value=mock_recent_posts), \
         patch("app.integrations.instagram.InstagramAdapter.fetch_media_insights", return_value=mock_media_insights):

        result = InstagramCommandService.sync_instagram_account(db, account)

        assert result["status"] == "success"
        assert result["follower_count"] == 1450
        assert result["synced_media_count"] == 1

        # Verify historical snapshot in PostgreSQL
        today = date.today()
        snap = db.query(InstagramMetricSnapshot).filter(
            InstagramMetricSnapshot.account_id == account.id,
            InstagramMetricSnapshot.date == today
        ).first()
        assert snap is not None
        assert snap.follower_count == 1450
        assert snap.reach == 2100
        assert snap.impressions == 4800

        # Verify media item in PostgreSQL
        media = db.query(InstagramMedia).filter(
            InstagramMedia.account_id == account.id,
            InstagramMedia.external_media_id == "999888111222"
        ).first()
        assert media is not None
        assert media.like_count == 88
        assert media.comments_count == 24
        assert media.reach_count == 950
        assert media.performance_score > 0.0

        # Idempotency test: Re-syncing today should update the existing snapshot, NOT create duplicates
        InstagramCommandService.sync_instagram_account(db, account)
        count = db.query(InstagramMetricSnapshot).filter(
            InstagramMetricSnapshot.account_id == account.id,
            InstagramMetricSnapshot.date == today
        ).count()
        assert count == 1


@pytest.mark.asyncio
async def test_meta_webhook_verification():
    """Verify GET /webhooks/meta responds correctly to Meta challenge."""
    from app.core.config import settings
    token = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "socialpilot_meta_webhook_secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid challenge
        resp = await client.get(f"/api/v1/webhooks/meta?hub.mode=subscribe&hub.challenge=115599&hub.verify_token={token}")
        assert resp.status_code == 200
        assert resp.text == "115599"

        # Invalid token
        bad_resp = await client.get("/api/v1/webhooks/meta?hub.mode=subscribe&hub.challenge=115599&hub.verify_token=wrong_token")
        assert bad_resp.status_code == 403


@pytest.mark.asyncio
async def test_meta_webhook_receiver_deduplication(db: Session):
    """Verify POST /webhooks/meta processes events and deduplicates duplicate deliveries."""
    from app.core.config import settings

    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "17841400000000001",
                "time": 1791234567,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment_999888",
                            "text": "Great Instagram command center update!",
                            "created_time": "2026-10-08T11:00:00+00:00",
                            "from": {"id": "user_11", "username": "ig_fan"},
                            "media": {"id": "media_777"}
                        }
                    }
                ]
            }
        ]
    }
    raw_bytes = json.dumps(payload).encode("utf-8")

    client_secret = settings.META_CLIENT_SECRET or "dummy_secret"
    sig = "sha256=" + hmac.new(client_secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch.object(settings, "META_CLIENT_SECRET", client_secret):
            try:
                # First delivery
                resp1 = await client.post(
                    "/api/v1/webhooks/meta",
                    content=raw_bytes,
                    headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"}
                )
                assert resp1.status_code == 200
                assert resp1.json()["events_processed"] == 1

                # Duplicate delivery (same payload)
                resp2 = await client.post(
                    "/api/v1/webhooks/meta",
                    content=raw_bytes,
                    headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"}
                )
                assert resp2.status_code == 200
                # Deduplication should skip processing the duplicate
                assert resp2.json()["events_processed"] == 0
            finally:
                try:
                    db.query(MetaWebhookEvent).delete()
                    db.commit()
                except Exception:
                    db.rollback()
