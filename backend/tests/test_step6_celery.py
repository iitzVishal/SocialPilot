import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.celery_app import celery_app
from app.tasks.publishing import publish_post_task, cancel_scheduled_task, _async_publish_post_execution
from app.db.base_class import Base
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus, PostStatus, PublishResultStatus
from app.schemas.post import PostCreate
from app.services.post_service import PostService
from app.core.security import encrypt_token

# SQLite in-memory engine for relational tables in test scope
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
def db_session(monkeypatch):
    session = TestingSessionLocal()
    monkeypatch.setattr("app.tasks.publishing.SessionLocal", lambda: session)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


import uuid


@pytest.fixture
def mock_user_and_accounts(db_session):
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"celery_tester_{uid}@socialpilot.test",
        hashed_password="fakehash12345678",
        full_name="Celery Tester",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    acc_tw = SocialAccount(
        user_id=user.id,
        platform=SocialPlatform.TWITTER,
        account_name="Celery Twitter",
        account_identifier="tw_celery",
        access_token=encrypt_token("tok_tw_123"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc_fb = SocialAccount(
        user_id=user.id,
        platform=SocialPlatform.FACEBOOK,
        account_name="Celery Facebook",
        account_identifier="fb_celery",
        access_token=encrypt_token("tok_fb_123"),
        connection_status=SocialAccountStatus.CONNECTED
    )
    acc_disc = SocialAccount(
        user_id=user.id,
        platform=SocialPlatform.LINKEDIN,
        account_name="Disconnected LinkedIn",
        account_identifier="li_disc",
        access_token=encrypt_token("tok_li_123"),
        connection_status=SocialAccountStatus.REVOKED
    )
    db_session.add_all([acc_tw, acc_fb, acc_disc])
    db_session.commit()
    db_session.refresh(acc_tw)
    db_session.refresh(acc_fb)
    db_session.refresh(acc_disc)

    return user, acc_tw, acc_fb, acc_disc


def test_1_celery_configuration():
    """Test 1: Celery application configuration, broker, serializers, and queues."""
    assert celery_app.main == "socialpilot"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    assert "app.tasks.publishing.publish_post_task" in celery_app.tasks
    assert "app.tasks.publishing.cancel_scheduled_task" in celery_app.tasks


@pytest.mark.asyncio
async def test_2_publish_task_execution_unconfigured_safeguard(db_session, mongo_test_db, mock_user_and_accounts, monkeypatch):
    """
    Test 2: publish_post_task executes without fake publishing.
    Verifies production adapters report PENDING_EXTERNAL_INTEGRATION and NOT_CONFIGURED.
    """
    monkeypatch.setattr("app.tasks.publishing.get_mongo_db", lambda: mongo_test_db)
    await mongo_test_db.posts.delete_many({})
    user, acc_tw, acc_fb, _ = mock_user_and_accounts

    # Create post in QUEUED status
    post_payload = PostCreate(
        base_content="Automated multi-platform background post via Celery",
        target_platforms=[SocialPlatform.TWITTER, SocialPlatform.FACEBOOK],
        target_accounts=[acc_tw.id, acc_fb.id]
    )
    post_doc = await PostService.create_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_in=post_payload
    )
    post_id = post_doc["id"]

    # Queue post
    await PostService.queue_post_for_publish(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_id=post_id
    )

    # Execute async publishing task
    res = await _async_publish_post_execution(post_id=post_id)
    assert res["post_id"] == post_id
    assert res["results_count"] == 2

    # Verify document in MongoDB
    from bson import ObjectId
    saved_post = await mongo_test_db.posts.find_one({"_id": ObjectId(post_id)})
    assert saved_post is not None
    assert saved_post["status"] in [PostStatus.FAILED.value, PostStatus.PARTIALLY_PUBLISHED.value]
    assert len(saved_post["publish_results"]) == 2
    for r in saved_post["publish_results"].values():
        assert r["status"] == PublishResultStatus.PENDING_EXTERNAL_INTEGRATION.value
        assert r["error_code"] == "NOT_CONFIGURED"
        assert r["external_post_id"] is None


@pytest.mark.asyncio
async def test_3_publish_task_skips_cancelled_post(db_session, mongo_test_db, mock_user_and_accounts, monkeypatch):
    """Test 3: Celery task skips post if it is cancelled or not claimable."""
    monkeypatch.setattr("app.tasks.publishing.get_mongo_db", lambda: mongo_test_db)
    await mongo_test_db.posts.delete_many({})
    user, acc_tw, _, _ = mock_user_and_accounts

    # Create and schedule post
    post_payload = PostCreate(
        base_content="Scheduled post to be cancelled",
        target_platforms=[SocialPlatform.TWITTER],
        target_accounts=[acc_tw.id]
    )
    post_doc = await PostService.create_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_in=post_payload
    )
    post_id = post_doc["id"]

    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    await PostService.schedule_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_id=post_id,
        scheduled_at=future_time
    )

    # User cancels post
    await PostService.cancel_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_id=post_id
    )

    # Celery worker attempts to publish cancelled post
    res = await _async_publish_post_execution(post_id=post_id)
    assert res["status"] == "SKIPPED_OR_ALREADY_CLAIMED"

    # Post remains CANCELLED
    from bson import ObjectId
    saved_post = await mongo_test_db.posts.find_one({"_id": ObjectId(post_id)})
    assert saved_post["status"] == PostStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_4_publish_task_handles_disconnected_account(db_session, mongo_test_db, mock_user_and_accounts, monkeypatch):
    """Test 4: Celery task records error when target account becomes disconnected."""
    monkeypatch.setattr("app.tasks.publishing.get_mongo_db", lambda: mongo_test_db)
    await mongo_test_db.posts.delete_many({})
    user, acc_tw, _, _ = mock_user_and_accounts

    post_payload = PostCreate(
        base_content="Post to disconnected account",
        target_platforms=[SocialPlatform.TWITTER],
        target_accounts=[acc_tw.id]
    )
    post_doc = await PostService.create_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_in=post_payload
    )
    post_id = post_doc["id"]

    await PostService.queue_post_for_publish(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_id=post_id
    )

    # Simulate account connection being revoked before Celery worker executes
    acc_tw.connection_status = SocialAccountStatus.REVOKED
    db_session.commit()

    res = await _async_publish_post_execution(post_id=post_id)

    from bson import ObjectId
    saved_post = await mongo_test_db.posts.find_one({"_id": ObjectId(post_id)})
    assert saved_post["status"] == PostStatus.FAILED.value
    results_list = list(saved_post["publish_results"].values())
    assert len(results_list) == 1
    assert results_list[0]["error_code"] == "ACCOUNT_DISCONNECTED"


@pytest.mark.asyncio
async def test_5_publish_task_platform_validation_error(db_session, mongo_test_db, mock_user_and_accounts, monkeypatch):
    """Test 5: Celery task records validation error when content exceeds platform limits."""
    monkeypatch.setattr("app.tasks.publishing.get_mongo_db", lambda: mongo_test_db)
    await mongo_test_db.posts.delete_many({})
    user, acc_tw, _, _ = mock_user_and_accounts

    # Twitter exceeds 280 characters
    long_content = "X" * 300
    post_payload = PostCreate(
        base_content=long_content,
        target_platforms=[SocialPlatform.TWITTER],
        target_accounts=[acc_tw.id]
    )
    post_doc = await PostService.create_post(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_in=post_payload
    )
    post_id = post_doc["id"]

    await PostService.queue_post_for_publish(
        mongo_db=mongo_test_db,
        db=db_session,
        user=user,
        post_id=post_id
    )
    res = await _async_publish_post_execution(post_id=post_id)

    from bson import ObjectId
    saved_post = await mongo_test_db.posts.find_one({"_id": ObjectId(post_id)})
    assert saved_post["status"] == PostStatus.FAILED.value
    results_list = list(saved_post["publish_results"].values())
    assert results_list[0]["error_code"] == "VALIDATION_ERROR"
    assert "exceeds 280 characters" in results_list[0]["error_message"]


def test_6_cancel_scheduled_task_revocation(monkeypatch):
    """Test 6: cancel_scheduled_task invokes celery control revocation."""
    called_args = {}

    def mock_revoke(task_id, terminate=True):
        called_args["task_id"] = task_id
        called_args["terminate"] = terminate

    monkeypatch.setattr(celery_app.control, "revoke", mock_revoke)
    res = cancel_scheduled_task("task_dummy_12345")
    assert res["task_id"] == "task_dummy_12345"
    assert res["status"] == "REVOKED"
    assert called_args["task_id"] == "task_dummy_12345"
    assert called_args["terminate"] is True
