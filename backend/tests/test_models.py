import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.enums import UserRole, SocialPlatform, SocialAccountStatus
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.social_account import SocialAccount


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    yield engine
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


def test_database_tables_exist(db_session):
    """Verify that all required tables exist in PostgreSQL public schema."""
    result = db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    )
    tables = {row[0] for row in result.fetchall()}
    assert "users" in tables
    assert "teams" in tables
    assert "team_members" in tables
    assert "social_accounts" in tables
    assert "alembic_version" in tables


def test_user_creation_and_query(db_session):
    """Verify creating and retrieving a user."""
    user = User(
        email="creator@socialpilot.test",
        hashed_password="$2b$12$securehashedpasswordexample12345",
        full_name="Creator User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.query(User).filter_by(email="creator@socialpilot.test").first()
    assert retrieved is not None
    assert retrieved.id is not None
    assert retrieved.full_name == "Creator User"
    assert retrieved.role == UserRole.CONTENT_CREATOR
    assert retrieved.is_active is True
    assert retrieved.created_at is not None


def test_team_and_membership_relationships(db_session):
    """Verify Team creation, ownership, and TeamMember relationships."""
    # 1. Create owner and member users
    owner = User(
        email="admin@socialpilot.test",
        hashed_password="$2b$12$securehashedpasswordexample12345",
        full_name="Admin Owner",
        role=UserRole.ADMINISTRATOR
    )
    member_user = User(
        email="marketer@socialpilot.test",
        hashed_password="$2b$12$securehashedpasswordexample12345",
        full_name="Marketing Pro",
        role=UserRole.MARKETING_TEAM
    )
    db_session.add_all([owner, member_user])
    db_session.commit()

    # 2. Create team
    team = Team(
        name="Marketing Alpha Workspace",
        description="Main workspace for social campaigns",
        owner_id=owner.id
    )
    db_session.add(team)
    db_session.commit()

    # 3. Add member
    membership = TeamMember(
        team_id=team.id,
        user_id=member_user.id,
        role=UserRole.MARKETING_TEAM
    )
    db_session.add(membership)
    db_session.commit()

    # 4. Verify relationships
    queried_team = db_session.query(Team).filter_by(id=team.id).first()
    assert queried_team.owner.email == "admin@socialpilot.test"
    assert len(queried_team.members) == 1
    assert queried_team.members[0].user.email == "marketer@socialpilot.test"
    assert queried_team.members[0].role == UserRole.MARKETING_TEAM


def test_social_account_creation_and_platform_enums(db_session):
    """Verify SocialAccount creation across all supported platforms."""
    user = User(
        email="business@socialpilot.test",
        hashed_password="$2b$12$securehashedpasswordexample12345",
        full_name="Business User",
        role=UserRole.BUSINESS_USER
    )
    db_session.add(user)
    db_session.commit()

    team = Team(
        name="Global Brand Team",
        owner_id=user.id
    )
    db_session.add(team)
    db_session.commit()

    # Supported platforms test: facebook, instagram, linkedin, twitter, youtube, pinterest
    platforms = [
        SocialPlatform.FACEBOOK,
        SocialPlatform.INSTAGRAM,
        SocialPlatform.LINKEDIN,
        SocialPlatform.TWITTER,
        SocialPlatform.YOUTUBE,
        SocialPlatform.PINTEREST
    ]

    for p in platforms:
        account = SocialAccount(
            user_id=user.id,
            team_id=team.id,
            platform=p,
            account_identifier=f"acct_{p.value}_12345",
            account_name=f"SocialPilot {p.value.capitalize()} Page",
            access_token="encrypted_mock_access_token_token_12345",
            refresh_token="encrypted_mock_refresh_token_12345",
            connection_status=SocialAccountStatus.CONNECTED,
            platform_permissions={"publish_posts": True, "read_insights": True}
        )
        db_session.add(account)
    db_session.commit()

    accounts = db_session.query(SocialAccount).filter_by(user_id=user.id).all()
    assert len(accounts) == 6
    account_platforms = {a.platform for a in accounts}
    assert account_platforms == set(platforms)

    # Test back_populates
    queried_user = db_session.query(User).filter_by(id=user.id).first()
    assert len(queried_user.social_accounts) == 6
    assert len(team.social_accounts) == 6
