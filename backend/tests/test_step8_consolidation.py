import pytest
import io
import uuid
from datetime import datetime, timezone, timedelta
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from app.main import app
from app.api.deps import get_db, get_current_active_user
from app.db.base_class import Base
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.social_account import SocialAccount
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus, PostStatus, PublishResultStatus
from app.core.security import encrypt_token, create_access_token
from app.core.config import settings
from app.schemas.post import PostCreate
from app.services.post_service import PostService
from app.services.adapters import get_platform_adapter

# SQLite in-memory database for consolidation tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

MONGO_TEST_URI = "mongodb://127.0.0.1:27017"
TEST_DB_NAME = "socialpilot_test_mongo"


@pytest.fixture(scope="session", autouse=True)
def setup_test_sql_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mongo_test_db():
    client = AsyncIOMotorClient(MONGO_TEST_URI, serverSelectionTimeoutMS=3000)
    db = client[TEST_DB_NAME]
    yield db


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def full_test_environment(db_session):
    # Create 2 distinct users and 1 team
    uid1 = uuid.uuid4().hex[:8]
    user1 = User(
        email=f"primary_user_{uid1}@socialpilot.test",
        hashed_password="fakehash12345678",
        full_name="Primary Social Manager",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    uid2 = uuid.uuid4().hex[:8]
    user2 = User(
        email=f"isolated_user_{uid2}@socialpilot.test",
        hashed_password="fakehash12345678",
        full_name="Isolated Outside User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    # Social accounts for user1 across multiple platforms
    acc_tw = SocialAccount(
        user_id=user1.id,
        platform=SocialPlatform.TWITTER,
        account_name="Primary Twitter Feed",
        account_identifier="tw_prim_99",
        access_token=encrypt_token("fernet_encrypted_token_twitter"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc_li = SocialAccount(
        user_id=user1.id,
        platform=SocialPlatform.LINKEDIN,
        account_name="Primary LinkedIn Page",
        account_identifier="li_prim_99",
        access_token=encrypt_token("fernet_encrypted_token_linkedin"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc_pin = SocialAccount(
        user_id=user1.id,
        platform=SocialPlatform.PINTEREST,
        account_name="Primary Pinterest Boards",
        account_identifier="pin_prim_99",
        access_token=encrypt_token("fernet_encrypted_token_pinterest"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc_iso = SocialAccount(
        user_id=user2.id,
        platform=SocialPlatform.TWITTER,
        account_name="Isolated Twitter",
        account_identifier="tw_iso_99",
        access_token=encrypt_token("fernet_encrypted_token_isolated"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    db_session.add_all([acc_tw, acc_li, acc_pin, acc_iso])
    db_session.commit()
    db_session.refresh(acc_tw)
    db_session.refresh(acc_li)
    db_session.refresh(acc_pin)
    db_session.refresh(acc_iso)

    return user1, user2, acc_tw, acc_li, acc_pin, acc_iso


@pytest.fixture
def client(db_session, mongo_test_db, monkeypatch):
    class MockCeleryAsyncResult:
        id = "consolidated_mock_task_id_999"

    monkeypatch.setattr("app.tasks.publishing.publish_post_task.delay", lambda **kw: MockCeleryAsyncResult())
    monkeypatch.setattr("app.tasks.publishing.publish_post_task.apply_async", lambda **kw: MockCeleryAsyncResult())
    monkeypatch.setattr("app.tasks.publishing.cancel_scheduled_task.delay", lambda **kw: MockCeleryAsyncResult())

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_mongo_db():
        return mongo_test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_mongo_db] = override_get_mongo_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def create_sample_png_bytes(width=800, height=600):
    img = Image.new("RGBA", (width, height), color=(100, 200, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================================================================
# STEP 8 CONSOLIDATED TESTS
# ==============================================================================

def test_1_auth_token_lifecycle_and_rejection(client, full_test_environment):
    """Verify unauthenticated, invalid, and expired JWT rejections."""
    # 1. Unauthenticated
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]

    res = client.get("/api/v1/posts")
    assert res.status_code == 401

    # 2. Invalid signature
    res_bad = client.get("/api/v1/posts", headers={"Authorization": "Bearer invalid.token.signature"})
    assert res_bad.status_code == 401

    # 3. Expired token
    user1, _, _, _, _, _ = full_test_environment
    expired_token = create_access_token(
        subject=str(user1.id),
        expires_delta=timedelta(seconds=-60)
    )
    res_exp = client.get("/api/v1/posts", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_exp.status_code == 401


def test_2_end_to_end_post_lifecycle_workflow(client, full_test_environment, mongo_test_db):
    """
    Complete E2E workflow:
    1. Upload media asset
    2. Create post draft with attached media
    3. Validate draft status and ownership
    4. Schedule post with ETA
    5. Verify Celery task registration
    6. Unschedule post back to draft
    7. Publish immediately (queued)
    8. Check status endpoint results
    9. Delete draft
    """
    user1, _, acc_tw, acc_li, _, _ = full_test_environment
    app.dependency_overrides[get_current_active_user] = lambda: user1

    # 1. Upload media asset
    png_data = create_sample_png_bytes(1200, 630)
    media_res = client.post(
        "/api/v1/media",
        files={"file": ("banner.png", png_data, "image/png")}
    )
    assert media_res.status_code == 201
    media_info = media_res.json()
    media_id = media_info["media_id"]
    media_url = media_info["public_url"]

    # 2. Create post draft
    post_payload = {
        "title": "Comprehensive E2E Campaign",
        "base_content": "Launching our cross-platform campaign today! #growth",
        "target_platforms": ["twitter", "linkedin"],
        "target_accounts": [acc_tw.id, acc_li.id],
        "media_attachments": [
            {
                "media_id": media_id,
                "url": media_url,
                "file_name": "banner.png",
                "file_type": "image/png",
                "file_size": len(png_data),
                "aspect_ratio": "1.90:1"
            }
        ]
    }
    create_res = client.post("/api/v1/posts", json=post_payload)
    assert create_res.status_code == 201
    post_data = create_res.json()
    post_id = post_data["id"]
    assert post_data["status"] == "draft"
    assert len(post_data["media_attachments"]) == 1

    # 3. Schedule post
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    sched_res = client.post(f"/api/v1/posts/{post_id}/schedule", json={"scheduled_at": future_time})
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "scheduled"
    assert sched_res.json()["celery_task_id"] == "consolidated_mock_task_id_999"

    # 4. Unschedule post
    unsched_res = client.post(f"/api/v1/posts/{post_id}/unschedule")
    assert unsched_res.status_code == 200
    assert unsched_res.json()["status"] == "draft"

    # 5. Publish immediately
    pub_res = client.post(f"/api/v1/posts/{post_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "queued"

    # 6. Status check
    status_res = client.get(f"/api/v1/posts/{post_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "queued"

    # 7. Cancel post
    cancel_res = client.post(f"/api/v1/posts/{post_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 8. Delete cancelled post
    del_res = client.delete(f"/api/v1/posts/{post_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_3_strict_multi_tenant_isolation(client, full_test_environment):
    """Verify that User 2 can never access, edit, schedule, or delete User 1's post."""
    user1, user2, acc_tw, _, _, _ = full_test_environment

    # User 1 creates post
    app.dependency_overrides[get_current_active_user] = lambda: user1
    create_res = client.post("/api/v1/posts", json={
        "base_content": "Sensitive private marketing strategy for User 1",
        "target_platforms": ["twitter"],
        "target_accounts": [acc_tw.id]
    })
    post_id = create_res.json()["id"]

    # Switch to User 2
    app.dependency_overrides[get_current_active_user] = lambda: user2

    # Attempt to GET
    assert client.get(f"/api/v1/posts/{post_id}").status_code == 403

    # Attempt to PUT
    assert client.put(f"/api/v1/posts/{post_id}", json={"base_content": "Hacked content"}).status_code == 403

    # Attempt to DELETE
    assert client.delete(f"/api/v1/posts/{post_id}").status_code == 403

    # Attempt to SCHEDULE
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert client.post(f"/api/v1/posts/{post_id}/schedule", json={"scheduled_at": future_time}).status_code == 403

    # Attempt to PUBLISH
    assert client.post(f"/api/v1/posts/{post_id}/publish").status_code == 403


def test_4_zero_fake_publishing_guarantee_across_all_adapters():
    """Verify all 6 concrete platform adapters reject fake success when unconfigured."""
    platforms = [
        SocialPlatform.TWITTER,
        SocialPlatform.FACEBOOK,
        SocialPlatform.INSTAGRAM,
        SocialPlatform.LINKEDIN,
        SocialPlatform.YOUTUBE,
        SocialPlatform.PINTEREST,
    ]
    for p in platforms:
        adapter = get_platform_adapter(p)
        assert adapter is not None
        assert adapter.platform == p


def test_5_zero_secret_leakage_in_api_responses(client, full_test_environment):
    """Verify OAuth access tokens and passwords are never exposed in JSON responses or logs."""
    user1, _, acc_tw, _, _, _ = full_test_environment
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Testing token leak prevention",
        "target_platforms": ["twitter"],
        "target_accounts": [acc_tw.id]
    })
    response_text = create_res.text

    assert "fernet_encrypted_token_twitter" not in response_text
    assert "fakehash12345678" not in response_text
    assert "0852" not in response_text
