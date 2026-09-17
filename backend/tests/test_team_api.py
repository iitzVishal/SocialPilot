import uuid
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.enums import UserRole

@pytest.fixture
def test_users_and_tokens():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create User A (team owner / administrator system role)
    user_a = User(
        email=f"user_a_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="User A",
        role=UserRole.ADMINISTRATOR,
        is_active=True
    )
    # Create User B (standard member / marketing team system role)
    user_b = User(
        email=f"user_b_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="User B",
        role=UserRole.MARKETING_TEAM,
        is_active=True
    )
    # Create User C (unauthorized user / content creator system role)
    user_c = User(
        email=f"user_c_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="User C",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add_all([user_a, user_b, user_c])
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
        "session": session
    }

    # Cleanup
    session.query(TeamMember).filter(TeamMember.user_id.in_([user_a.id, user_b.id, user_c.id])).delete(synchronize_session=False)
    session.query(Team).filter(Team.owner_id.in_([user_a.id, user_b.id, user_c.id])).delete(synchronize_session=False)
    session.query(User).filter(User.id.in_([user_a.id, user_b.id, user_c.id])).delete(synchronize_session=False)
    session.commit()
    session.close()
    engine.dispose()

@pytest.mark.asyncio
async def test_team_create_and_read(test_users_and_tokens):
    """Test team creation and retrieval endpoints."""
    token_a = test_users_and_tokens["token_a"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create team
        res = await client.post(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "name": "Alpha Team",
                "description": "The primary campaign workspace"
            }
        )
        assert res.status_code == 201
        team_data = res.json()
        assert team_data["name"] == "Alpha Team"
        assert team_data["description"] == "The primary campaign workspace"
        assert team_data["id"] is not None

        # Fetch list of teams
        res_list = await client.get(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_list.status_code == 200
        teams = res_list.json()
        assert any(t["id"] == team_data["id"] for t in teams)

        # Get details by ID
        res_detail = await client.get(
            f"/api/v1/teams/{team_data['id']}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_detail.status_code == 200
        assert res_detail.json()["name"] == "Alpha Team"

@pytest.mark.asyncio
async def test_team_unauthorized_access(test_users_and_tokens):
    """Test that unauthorized users cannot view, edit, or delete a team."""
    token_a = test_users_and_tokens["token_a"]
    token_c = test_users_and_tokens["token_c"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create team as User A
        res = await client.post(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "A Team"}
        )
        team_id = res.json()["id"]

        # Attempt to read as User C
        res_get = await client.get(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_c}"}
        )
        assert res_get.status_code == 403

        # Attempt to edit as User C
        res_put = await client.put(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_c}"},
            json={"name": "Hacked Team Name"}
        )
        assert res_put.status_code == 403

        # Attempt to delete as User C
        res_del = await client.delete(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_c}"}
        )
        assert res_del.status_code == 403

@pytest.mark.asyncio
async def test_team_update_and_delete(test_users_and_tokens):
    """Test update and deletion of team."""
    token_a = test_users_and_tokens["token_a"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create team
        res = await client.post(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Beta Workspace"}
        )
        team_id = res.json()["id"]

        # Update team details
        res_update = await client.put(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Beta Updated", "description": "New description"}
        )
        assert res_update.status_code == 200
        assert res_update.json()["name"] == "Beta Updated"
        assert res_update.json()["description"] == "New description"

        # Delete team
        res_del = await client.delete(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True

        # Verify 404 on subsequent get
        res_get = await client.get(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_get.status_code == 404

@pytest.mark.asyncio
async def test_member_management_lifecycle(test_users_and_tokens):
    """Test adding, listing, updating, and removing team members."""
    token_a = test_users_and_tokens["token_a"]
    token_b = test_users_and_tokens["token_b"]
    user_b = test_users_and_tokens["user_b"]
    user_c = test_users_and_tokens["user_c"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create team as User A
        res = await client.post(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Collaborative Team"}
        )
        team_id = res.json()["id"]

        # 1. Add User B to the team
        res_add = await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"email": user_b.email, "role": "content_creator"}
        )
        assert res_add.status_code == 201
        assert res_add.json()["user"]["email"] == user_b.email
        assert res_add.json()["role"] == "content_creator"

        # 2. Duplicate membership restriction check
        res_add_dup = await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"email": user_b.email, "role": "marketing_team"}
        )
        assert res_add_dup.status_code == 400

        # 3. Non-existent user addition check
        res_add_missing = await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"email": "does_not_exist_email@socialpilot.test"}
        )
        assert res_add_missing.status_code == 404

        # 4. List team members (should see User A as Admin and User B as Content Creator)
        res_list = await client.get(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_list.status_code == 200
        members = res_list.json()
        assert len(members) == 2
        emails = {m["user"]["email"] for m in members}
        assert user_b.email in emails

        # 5. Update User B's role to marketing_team
        res_role = await client.put(
            f"/api/v1/teams/{team_id}/members/{user_b.id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"role": "marketing_team"}
        )
        assert res_role.status_code == 200
        assert res_role.json()["role"] == "marketing_team"

        # 6. Try to update Owner's role (should be rejected)
        user_a = test_users_and_tokens["user_a"]
        res_role_owner = await client.put(
            f"/api/v1/teams/{team_id}/members/{user_a.id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"role": "content_creator"}
        )
        assert res_role_owner.status_code == 400

        # 7. Remove User B from team
        res_remove = await client.delete(
            f"/api/v1/teams/{team_id}/members/{user_b.id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_remove.status_code == 200
        assert res_remove.json()["success"] is True

        # 8. Try to remove Owner (should be rejected)
        res_remove_owner = await client.delete(
            f"/api/v1/teams/{team_id}/members/{user_a.id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_remove_owner.status_code == 400
