import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.models.enums import UserRole
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember

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

def test_team_member_duplicate_membership_prevention(db_session):
    """Verify uq_team_member unique constraint prevents duplicate memberships."""
    # Create test users
    owner = User(
        email="team_owner@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.ADMINISTRATOR
    )
    member = User(
        email="team_member@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.CONTENT_CREATOR
    )
    db_session.add_all([owner, member])
    db_session.commit()

    # Create team
    team = Team(name="Test Team", owner_id=owner.id)
    db_session.add(team)
    db_session.commit()

    # Add member first time
    mem1 = TeamMember(team_id=team.id, user_id=member.id, role=UserRole.CONTENT_CREATOR)
    db_session.add(mem1)
    db_session.commit()

    # Add member second time (should fail unique constraint)
    mem2 = TeamMember(team_id=team.id, user_id=member.id, role=UserRole.MARKETING_TEAM)
    db_session.add(mem2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_team_member_invalid_user_fk(db_session):
    """Verify foreign key constraint on user_id in team_members."""
    owner = User(
        email="team_owner_invalid_user@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.ADMINISTRATOR
    )
    db_session.add(owner)
    db_session.commit()

    team = Team(name="Test Team Invalid User", owner_id=owner.id)
    db_session.add(team)
    db_session.commit()

    # Attempt to insert team member with non-existent user_id
    invalid_mem = TeamMember(team_id=team.id, user_id=99999, role=UserRole.CONTENT_CREATOR)
    db_session.add(invalid_mem)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_team_member_invalid_team_fk(db_session):
    """Verify foreign key constraint on team_id in team_members."""
    user = User(
        email="team_member_invalid_team@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.CONTENT_CREATOR
    )
    db_session.add(user)
    db_session.commit()

    # Attempt to insert team member with non-existent team_id
    invalid_mem = TeamMember(team_id=99999, user_id=user.id, role=UserRole.CONTENT_CREATOR)
    db_session.add(invalid_mem)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_team_deletion_cascade(db_session):
    """Verify that deleting a team deletes associated team members (cascade delete)."""
    owner = User(
        email="team_cascade_owner@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.ADMINISTRATOR
    )
    member = User(
        email="team_cascade_member@socialpilot.test",
        hashed_password="hashed_password",
        role=UserRole.CONTENT_CREATOR
    )
    db_session.add_all([owner, member])
    db_session.commit()

    team = Team(name="Test Cascade Team", owner_id=owner.id)
    db_session.add(team)
    db_session.commit()

    membership = TeamMember(team_id=team.id, user_id=member.id, role=UserRole.CONTENT_CREATOR)
    db_session.add(membership)
    db_session.commit()

    # Verify membership exists
    assert db_session.query(TeamMember).filter_by(team_id=team.id, user_id=member.id).first() is not None

    # Delete team
    db_session.delete(team)
    db_session.commit()

    # Verify membership was deleted automatically
    assert db_session.query(TeamMember).filter_by(team_id=team.id, user_id=member.id).first() is None
