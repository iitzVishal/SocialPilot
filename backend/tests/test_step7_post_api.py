import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.api.deps import get_db, get_current_active_user
from app.db.base_class import Base
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus, PostStatus, PublishResultStatus
from app.core.security import encrypt_token
from app.services.post_service import PostService
from app.core.celery_app import celery_app

# SQLite in-memory engine for API integration testing
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
def test_users_and_accounts(db_session):
    uid1 = uuid.uuid4().hex[:8]
    user1 = User(
        email=f"author_{uid1}@socialpilot.test",
        hashed_password="fakehash12345678",
        full_name="Post Author User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    uid2 = uuid.uuid4().hex[:8]
    user2 = User(
        email=f"other_{uid2}@socialpilot.test",
        hashed_password="fakehash12345678",
        full_name="Other Isolated User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    acc1 = SocialAccount(
        user_id=user1.id,
        platform=SocialPlatform.TWITTER,
        account_name="Author Twitter Account",
        account_identifier="tw_auth_123",
        access_token=encrypt_token("super_secret_auth_token_999"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc2 = SocialAccount(
        user_id=user2.id,
        platform=SocialPlatform.TWITTER,
        account_name="Other Twitter Account",
        account_identifier="tw_other_123",
        access_token=encrypt_token("super_secret_other_token_888"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()
    db_session.refresh(acc1)
    db_session.refresh(acc2)

    return user1, user2, acc1, acc2


@pytest.fixture
def client(db_session, mongo_test_db, monkeypatch):
    # Mock celery task dispatch to prevent external network traffic in test suite
    class MockCeleryAsyncResult:
        id = "mock_task_uuid_12345"

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


def test_1_create_post_draft_success(client, test_users_and_accounts, mongo_test_db):
    """Test 1: Authenticated user creates a draft post."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    payload = {
        "title": "My First Social Campaign",
        "base_content": "Excited to launch our product today! #launch",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    }
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My First Social Campaign"
    assert data["status"] == "draft"
    assert data["user_id"] == user1.id
    assert "id" in data
    # Guarantee no sensitive token leaked
    assert "super_secret_auth_token_999" not in response.text


def test_2_create_post_unauthenticated(client):
    """Test 2: Unauthenticated POST /api/v1/posts returns 401."""
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]

    payload = {
        "base_content": "Unauthorized post attempt",
        "target_platforms": ["twitter"],
        "target_accounts": [1]
    }
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 401


def test_3_create_post_unauthorized_target_account(client, test_users_and_accounts):
    """Test 3: User cannot create post with an account belonging to another user."""
    user1, user2, _, acc2 = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    payload = {
        "base_content": "Hijack attempt",
        "target_platforms": ["twitter"],
        "target_accounts": [acc2.id]  # Belongs to user2
    }
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code in [403, 404]


def test_4_list_posts_with_isolation(client, test_users_and_accounts, mongo_test_db):
    """Test 4: User only sees their own posts in listing."""
    user1, user2, acc1, acc2 = test_users_and_accounts

    # Create post for user1
    app.dependency_overrides[get_current_active_user] = lambda: user1
    client.post("/api/v1/posts", json={
        "base_content": "User 1 post content",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })

    # Create post for user2
    app.dependency_overrides[get_current_active_user] = lambda: user2
    client.post("/api/v1/posts", json={
        "base_content": "User 2 post content",
        "target_platforms": ["twitter"],
        "target_accounts": [acc2.id]
    })

    # Query as user1
    app.dependency_overrides[get_current_active_user] = lambda: user1
    res1 = client.get("/api/v1/posts")
    assert res1.status_code == 200
    items1 = res1.json()["items"]
    assert all(item["user_id"] == user1.id for item in items1)


def test_5_and_6_get_post_and_forbidden_access(client, test_users_and_accounts):
    """Test 5 & 6: User can get own post; other user is denied access (403)."""
    user1, user2, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Private draft for user 1",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })
    post_id = create_res.json()["id"]

    # User 1 can view
    get_res = client.get(f"/api/v1/posts/{post_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == post_id

    # User 2 receives 403 Forbidden
    app.dependency_overrides[get_current_active_user] = lambda: user2
    forbidden_res = client.get(f"/api/v1/posts/{post_id}")
    assert forbidden_res.status_code == 403


def test_7_update_draft_post(client, test_users_and_accounts):
    """Test 7: Update post in DRAFT state."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Original draft content",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })
    post_id = create_res.json()["id"]

    update_res = client.put(f"/api/v1/posts/{post_id}", json={
        "base_content": "Updated draft content with extra info"
    })
    assert update_res.status_code == 200
    assert update_res.json()["base_content"] == "Updated draft content with extra info"


def test_8_delete_draft_post(client, test_users_and_accounts):
    """Test 8: Hard delete a draft post."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Draft to delete",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })
    post_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/posts/{post_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm it's gone
    get_res = client.get(f"/api/v1/posts/{post_id}")
    assert get_res.status_code == 404


def test_9_and_10_schedule_and_unschedule_post(client, test_users_and_accounts):
    """Test 9 & 10: Schedule a draft post and unschedule it back to draft."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Scheduled content for tomorrow",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })
    post_id = create_res.json()["id"]

    future_utc = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    sched_res = client.post(f"/api/v1/posts/{post_id}/schedule", json={
        "scheduled_at": future_utc
    })
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "scheduled"
    assert sched_res.json()["celery_task_id"] == "mock_task_uuid_12345"

    # Unschedule
    unsched_res = client.post(f"/api/v1/posts/{post_id}/unschedule")
    assert unsched_res.status_code == 200
    assert unsched_res.json()["status"] == "draft"


def test_11_publish_post_immediately(client, test_users_and_accounts):
    """Test 11: Immediate publish transitions to QUEUED and attaches task ID."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Publish immediately test",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id]
    })
    post_id = create_res.json()["id"]

    pub_res = client.post(f"/api/v1/posts/{post_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "queued"
    assert pub_res.json()["celery_task_id"] == "mock_task_uuid_12345"


def test_12_and_13_cancel_and_status_endpoints(client, test_users_and_accounts):
    """Test 12 & 13: Cancel a queued post and check status endpoint."""
    user1, _, acc1, _ = test_users_and_accounts
    app.dependency_overrides[get_current_active_user] = lambda: user1

    create_res = client.post("/api/v1/posts", json={
        "base_content": "Post to cancel",
        "target_platforms": ["twitter"],
        "target_accounts": [acc1.id],
        "publish_now": True
    })
    post_id = create_res.json()["id"]

    # Cancel post
    cancel_res = client.post(f"/api/v1/posts/{post_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Check status endpoint
    status_res = client.get(f"/api/v1/posts/{post_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "cancelled"
    assert "publish_results" in status_res.json()
