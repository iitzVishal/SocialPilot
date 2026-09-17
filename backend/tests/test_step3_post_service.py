import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.core.config import settings
from app.db.base_class import Base
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus, PostStatus, PublishResultStatus
from app.schemas.post import PostCreate, PostUpdate, AccountPublishResult
from app.services.post_service import PostService, ensure_post_indexes


@pytest.fixture
def mongo_test_db():
    client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
    db = client["socialpilot_test_mongo"]
    yield db
    client.close()


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_user(db_session):
    import uuid
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"author_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="Post Author",
        role=UserRole.CONTENT_CREATOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    import uuid
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"other_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="Other User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_accounts(db_session, sample_user):
    acc1 = SocialAccount(
        user_id=sample_user.id,
        platform=SocialPlatform.FACEBOOK,
        account_name="Facebook Page",
        account_identifier="fb_12345",
        access_token="enc_token_fb",
        connection_status=SocialAccountStatus.CONNECTED,
    )
    acc2 = SocialAccount(
        user_id=sample_user.id,
        platform=SocialPlatform.TWITTER,
        account_name="Twitter Feed",
        account_identifier="tw_12345",
        access_token="enc_token_tw",
        connection_status=SocialAccountStatus.CONNECTED,
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()
    db_session.refresh(acc1)
    db_session.refresh(acc2)
    return [acc1, acc2]


@pytest.mark.asyncio
async def test_1_and_15_index_creation_and_post_create(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 1 & 15: Index creation and creating a valid draft post in MongoDB."""
    await mongo_test_db["posts"].delete_many({})
    await ensure_post_indexes(mongo_test_db)
    indexes = await mongo_test_db["posts"].index_information()
    assert "idx_user_status_created" in indexes
    assert "idx_status_scheduled" in indexes
    assert "idx_target_accounts" in indexes

    post_in = PostCreate(
        title="Product Launch",
        base_content="Check out our new feature!",
        target_platforms=[SocialPlatform.FACEBOOK, SocialPlatform.TWITTER],
        target_accounts=[sample_accounts[0].id, sample_accounts[1].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    assert created["id"] is not None
    assert created["user_id"] == sample_user.id
    assert created["status"] == PostStatus.DRAFT.value
    assert created["title"] == "Product Launch"
    assert created["target_accounts"] == [sample_accounts[0].id, sample_accounts[1].id]


@pytest.mark.asyncio
async def test_2_and_3_post_retrieval_and_update(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 2 & 3: Post retrieval and updating draft content."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Initial text",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    fetched = await PostService.get_post_by_id(mongo_test_db, db_session, sample_user, post_id)
    assert fetched["base_content"] == "Initial text"

    update_in = PostUpdate(base_content="Updated text body")
    updated = await PostService.update_post(mongo_test_db, db_session, sample_user, post_id, update_in)
    assert updated["base_content"] == "Updated text body"


@pytest.mark.asyncio
async def test_4_user_ownership_enforcement(mongo_test_db, db_session, sample_user, other_user, sample_accounts):
    """Test 4: Unauthorized user cannot read or update another user's post."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Private draft",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    with pytest.raises(HTTPException) as exc_info:
        await PostService.get_post_by_id(mongo_test_db, db_session, other_user, post_id)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        await PostService.update_post(mongo_test_db, db_session, other_user, post_id, PostUpdate(base_content="Hacked"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_5_team_authorization(mongo_test_db, db_session, sample_user, other_user, sample_accounts):
    """Test 5: Team member can access team posts."""
    await mongo_test_db["posts"].delete_many({})
    team = Team(name="Growth Team", owner_id=sample_user.id)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    membership = TeamMember(team_id=team.id, user_id=other_user.id, role=UserRole.MARKETING_TEAM)
    db_session.add(membership)
    db_session.commit()

    post_in = PostCreate(
        team_id=team.id,
        base_content="Team Shared Post",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    team_post = await PostService.get_post_by_id(mongo_test_db, db_session, other_user, post_id)
    assert team_post["base_content"] == "Team Shared Post"


@pytest.mark.asyncio
async def test_6_and_13_target_account_authorization_and_platform_mismatch(mongo_test_db, db_session, sample_user, other_user, sample_accounts):
    """Test 6 & 13: Rejection if account does not belong to user or platform doesn't match."""
    await mongo_test_db["posts"].delete_many({})
    foreign_account = SocialAccount(
        user_id=other_user.id,
        platform=SocialPlatform.LINKEDIN,
        account_name="Foreign Profile",
        account_identifier="li_foreign",
        access_token="enc_token",
        connection_status=SocialAccountStatus.CONNECTED,
    )
    db_session.add(foreign_account)
    db_session.commit()
    db_session.refresh(foreign_account)

    # 6. Cannot use another user's account
    post_in_foreign = PostCreate(
        base_content="Post on someone else's account",
        target_platforms=[SocialPlatform.LINKEDIN],
        target_accounts=[foreign_account.id],
    )
    with pytest.raises(HTTPException) as exc_info:
        await PostService.create_post(mongo_test_db, db_session, sample_user, post_in_foreign)
    assert exc_info.value.status_code == 403

    # 13. Platform mismatch (Account is Facebook, but target_platforms says LinkedIn)
    post_in_mismatch = PostCreate(
        base_content="Mismatch test",
        target_platforms=[SocialPlatform.LINKEDIN],
        target_accounts=[sample_accounts[0].id],  # sample_accounts[0] is Facebook
    )
    with pytest.raises(HTTPException) as exc_info:
        await PostService.create_post(mongo_test_db, db_session, sample_user, post_in_mismatch)
    assert exc_info.value.status_code == 400
    assert "not in target platforms list" in exc_info.value.detail


@pytest.mark.asyncio
async def test_7_8_state_machine_valid_and_invalid_transitions(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 7 & 8: Validate allowed and disallowed lifecycle state transitions."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="State Machine Test",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]
    assert created["status"] == PostStatus.DRAFT.value

    # Valid: DRAFT -> SCHEDULED
    future_time = datetime.now(timezone.utc) + timedelta(days=3)
    scheduled = await PostService.schedule_post(mongo_test_db, db_session, sample_user, post_id, future_time)
    assert scheduled["status"] == PostStatus.SCHEDULED.value

    # Valid: SCHEDULED -> QUEUED
    queued = await PostService.queue_post_for_publish(mongo_test_db, db_session, sample_user, post_id)
    assert queued["status"] == PostStatus.QUEUED.value

    # Invalid: Cannot directly schedule from QUEUED
    with pytest.raises(HTTPException) as exc_info:
        await PostService.schedule_post(mongo_test_db, db_session, sample_user, post_id, future_time)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_9_draft_hard_deletion(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 9: DRAFT posts can be hard deleted."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Disposable Draft",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    deleted = await PostService.delete_post(mongo_test_db, db_session, sample_user, post_id)
    assert deleted is True

    # Verify not found
    with pytest.raises(HTTPException) as exc_info:
        await PostService.get_post_by_id(mongo_test_db, db_session, sample_user, post_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_10_scheduled_cancellation_and_unscheduling(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 10: SCHEDULED posts can be unscheduled (to DRAFT) or cancelled."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Schedule Management",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    future_time = datetime.now(timezone.utc) + timedelta(days=1)
    await PostService.schedule_post(mongo_test_db, db_session, sample_user, post_id, future_time)

    # 10a. Unschedule back to draft
    unscheduled = await PostService.unschedule_post(mongo_test_db, db_session, sample_user, post_id)
    assert unscheduled["status"] == PostStatus.DRAFT.value
    assert unscheduled["scheduled_at"] is None

    # 10b. Re-schedule and then cancel
    await PostService.schedule_post(mongo_test_db, db_session, sample_user, post_id, future_time)
    cancelled = await PostService.cancel_post(mongo_test_db, db_session, sample_user, post_id)
    assert cancelled["status"] == PostStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_11_atomic_state_transition_claim(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 11: Worker atomic claim transitions QUEUED -> PUBLISHING exactly once."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Atomic claim post",
        target_platforms=[SocialPlatform.FACEBOOK],
        target_accounts=[sample_accounts[0].id],
        publish_now=True,  # Initially QUEUED
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]
    assert created["status"] == PostStatus.QUEUED.value

    # First worker claims task -> SUCCESS
    claimed1 = await PostService.atomic_claim_for_publishing(mongo_test_db, post_id)
    assert claimed1 is not None
    assert claimed1["status"] == PostStatus.PUBLISHING.value

    # Second worker attempts to claim same post -> FAILS (returns None)
    claimed2 = await PostService.atomic_claim_for_publishing(mongo_test_db, post_id)
    assert claimed2 is None


@pytest.mark.asyncio
async def test_12_publish_result_persistence_and_partial_failure(mongo_test_db, db_session, sample_user, sample_accounts):
    """Test 12: Record individual account results (FB success, TW failure) -> PARTIALLY_PUBLISHED."""
    await mongo_test_db["posts"].delete_many({})
    acc_fb = sample_accounts[0]
    acc_tw = sample_accounts[1]

    post_in = PostCreate(
        base_content="Multi-platform post",
        target_platforms=[SocialPlatform.FACEBOOK, SocialPlatform.TWITTER],
        target_accounts=[acc_fb.id, acc_tw.id],
        publish_now=True,
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    await PostService.atomic_claim_for_publishing(mongo_test_db, post_id)

    # Simulate 1 success and 1 failed dispatch
    results = {
        str(acc_fb.id): AccountPublishResult(
            account_id=acc_fb.id,
            platform=SocialPlatform.FACEBOOK,
            status=PublishResultStatus.SUCCESS,
            external_post_id="fb_live_post_1001",
            published_at=datetime.now(timezone.utc),
            attempt_count=1,
        ),
        str(acc_tw.id): AccountPublishResult(
            account_id=acc_tw.id,
            platform=SocialPlatform.TWITTER,
            status=PublishResultStatus.FAILED,
            error_code="RATE_LIMITED",
            error_message="Twitter rate limit exceeded",
            retryable=True,
            attempt_count=1,
        ),
    }

    recorded = await PostService.record_publish_results(mongo_test_db, post_id, results)
    assert recorded["status"] == PostStatus.PARTIALLY_PUBLISHED.value
    assert recorded["publish_results"][str(acc_fb.id)]["status"] == PublishResultStatus.SUCCESS.value
    assert recorded["publish_results"][str(acc_tw.id)]["status"] == PublishResultStatus.FAILED.value


@pytest.mark.asyncio
async def test_14_required_target_account_validation(mongo_test_db, db_session, sample_user):
    """Test 14: Draft without target accounts cannot be scheduled or queued."""
    await mongo_test_db["posts"].delete_many({})
    post_in = PostCreate(
        base_content="Draft with no target accounts",
        target_platforms=[],
        target_accounts=[],
    )
    created = await PostService.create_post(mongo_test_db, db_session, sample_user, post_in)
    post_id = created["id"]

    future_time = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(HTTPException) as exc_info:
        await PostService.schedule_post(mongo_test_db, db_session, sample_user, post_id, future_time)
    assert exc_info.value.status_code == 400
    assert "without selected target accounts" in exc_info.value.detail
