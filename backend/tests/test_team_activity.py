import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.team_invitation import TeamInvitation
from app.models.enums import UserRole, TeamInvitationStatus
from app.services.audit_service import AuditService, sanitize_metadata
from app.db.mongo import get_mongo_db

@pytest.fixture
def test_setup():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User A: Owner/Admin
    user_a = User(
        email=f"owner_{uid}@socialpilot.test",
        hashed_password="hashed_password_123",
        full_name="Workspace Owner",
        role=UserRole.ADMINISTRATOR,
        is_active=True
    )
    # User B: Member
    user_b = User(
        email=f"member_{uid}@socialpilot.test",
        hashed_password="hashed_password_123",
        full_name="Workspace Member",
        role=UserRole.MARKETING_TEAM,
        is_active=True
    )
    # User C: Outsider
    user_c = User(
        email=f"outsider_{uid}@socialpilot.test",
        hashed_password="hashed_password_123",
        full_name="Outsider User",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add_all([user_a, user_b, user_c])
    session.commit()

    # Team
    team = Team(
        name=f"Audit Test Team {uid}",
        description="Testing activity audit logging",
        owner_id=user_a.id
    )
    session.add(team)
    session.commit()

    # Memberships
    m_a = TeamMember(team_id=team.id, user_id=user_a.id, role=UserRole.ADMINISTRATOR)
    m_b = TeamMember(team_id=team.id, user_id=user_b.id, role=UserRole.CONTENT_CREATOR)
    session.add_all([m_a, m_b])
    session.commit()

    token_a = create_access_token(subject=user_a.id)
    token_b = create_access_token(subject=user_b.id)
    token_c = create_access_token(subject=user_c.id)

    yield {
        "user_a": user_a,
        "token_a": token_a,
        "user_b": user_b,
        "token_b": token_b,
        "user_c": user_c,
        "token_c": token_c,
        "team": team,
        "session": session
    }

    session.close()


@pytest.mark.asyncio
async def test_authenticated_member_can_fetch_activity(test_setup):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {test_setup['token_b']}"}
        res = await ac.get(f"/api/v1/teams/{test_setup['team'].id}/activity", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data


@pytest.mark.asyncio
async def test_non_member_receives_403(test_setup):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {test_setup['token_c']}"}
        res = await ac.get(f"/api/v1/teams/{test_setup['team'].id}/activity", headers=headers)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_invalid_team_id_not_found(test_setup):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {test_setup['token_a']}"}
        res = await ac.get("/api/v1/teams/999999/activity", headers=headers)
        assert res.status_code in [404, 403]


@pytest.mark.asyncio
@patch("app.tasks.email.send_invitation_email_task.delay")
async def test_invitation_creation_and_role_change_logging(mock_email_delay, test_setup):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers_a = {"Authorization": f"Bearer {test_setup['token_a']}"}
        
        # 1. Create invitation
        inv_payload = {"email": f"new_invite_{uuid.uuid4().hex[:6]}@test.com", "role": "marketing_team"}
        inv_res = await ac.post(f"/api/v1/teams/{test_setup['team'].id}/invitations", json=inv_payload, headers=headers_a)
        assert inv_res.status_code == 201

        # 2. Update member role
        role_res = await ac.put(
            f"/api/v1/teams/{test_setup['team'].id}/members/{test_setup['user_b'].id}",
            json={"role": "marketing_team"},
            headers=headers_a
        )
        assert role_res.status_code == 200

        # 3. Check activity log
        act_res = await ac.get(f"/api/v1/teams/{test_setup['team'].id}/activity", headers=headers_a)
        assert act_res.status_code == 200
        data = act_res.json()
        actions = [item["action"] for item in data["items"]]
        assert "invitation_create" in actions or "member_role_change" in actions


@pytest.mark.asyncio
async def test_sensitive_metadata_sanitizer():
    raw_meta = {
        "password": "secret_password_123",
        "access_token": "bearer_xyz_123",
        "normal_key": "safe_value",
        "nested": {
            "smtp_password": "smtp_secret",
            "info": "public"
        }
    }
    cleaned = sanitize_metadata(raw_meta)
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["access_token"] == "[REDACTED]"
    assert cleaned["normal_key"] == "safe_value"
    assert cleaned["nested"]["smtp_password"] == "[REDACTED]"
    assert cleaned["nested"]["info"] == "public"


@pytest.mark.asyncio
async def test_audit_log_fault_tolerance(test_setup):
    class BrokenMongo:
        is_mock = True
        class BrokenCollection:
            async def insert_one(self, doc):
                raise RuntimeError("Simulated Mongo Database Exception")
        def __getitem__(self, item):
            return self.BrokenCollection()

    result = await AuditService.log_event(
        mongo_db=BrokenMongo(),
        team_id=test_setup["team"].id,
        action="test_action",
        entity_type="test",
        description="Fault tolerance test"
    )
    assert result is False
