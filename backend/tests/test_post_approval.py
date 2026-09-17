import uuid
from datetime import datetime, timedelta, timezone
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
from app.models.enums import UserRole, PostStatus

@pytest.fixture
def approval_test_setup():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User A (Owner / Admin)
    user_a = User(
        email=f"usera_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="User A (Owner)",
        role=UserRole.ADMINISTRATOR,
        is_active=True
    )
    # User B (Creator)
    user_b = User(
        email=f"userb_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="User B (Creator)",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    # User C (Stranger from another team)
    user_c = User(
        email=f"userc_{uid}@socialpilot.test",
        hashed_password="hashed_password",
        full_name="User C (Stranger)",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    session.add_all([user_a, user_b, user_c])
    session.commit()

    # Team A with require_post_approval = True
    team_a = Team(
        name="Approval Workspace",
        owner_id=user_a.id,
        require_post_approval=True
    )
    # Team B (Stranger's workspace)
    team_b = Team(
        name="Stranger Workspace",
        owner_id=user_c.id,
        require_post_approval=False
    )
    session.add_all([team_a, team_b])
    session.commit()

    # Memberships
    memb_a_owner = TeamMember(team_id=team_a.id, user_id=user_a.id, role=UserRole.ADMINISTRATOR)
    memb_a_creator = TeamMember(team_id=team_a.id, user_id=user_b.id, role=UserRole.CONTENT_CREATOR)
    session.add_all([memb_a_owner, memb_a_creator])
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
        "team_a_id": team_a.id,
        "team_b_id": team_b.id,
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
async def test_full_approval_workflow_lifecycle(approval_test_setup):
    token_a = approval_test_setup["token_a"]
    token_b = approval_test_setup["token_b"]
    token_c = approval_test_setup["token_c"]
    team_a_id = approval_test_setup["team_a_id"]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Content creator (User B) creates draft in Team A
        res_create = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "title": "Approval Test Post",
                "base_content": "Draft Content",
                "team_id": team_a_id,
                "target_accounts": [],
                "target_platforms": []
            }
        )
        assert res_create.status_code == 201
        post_id = res_create.json()["id"]
        assert res_create.json()["status"] == "draft"

        # 2. Content creator tries to publish directly -> 403 Forbidden (no targets, but also blocked by approval check)
        res_pub = await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_pub.status_code == 403 or res_pub.status_code == 400

        # Let's verify: submit for approval transition
        res_submit = await client.post(
            f"/api/v1/posts/{post_id}/submit-for-approval",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_submit.status_code == 200
        assert res_submit.json()["status"] == "pending_approval"
        assert res_submit.json()["approval_requested_at"] is not None

        # 3. Content creator tries to approve own post -> 403 Forbidden
        res_approve_self = await client.post(
            f"/api/v1/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_approve_self.status_code == 403

        # 4. Stranger (User C) tries to approve -> 403 Forbidden
        res_approve_stranger = await client.post(
            f"/api/v1/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {token_c}"}
        )
        assert res_approve_stranger.status_code == 403

        # 5. Team Owner (User A) rejects post
        res_reject = await client.post(
            f"/api/v1/posts/{post_id}/reject",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"reason": "Please fix grammatical errors."}
        )
        assert res_reject.status_code == 200
        assert res_reject.json()["status"] == "rejected"
        assert res_reject.json()["rejection_reason"] == "Please fix grammatical errors."

        # 6. Creator (User B) edits rejected post -> status reverts back to draft
        res_update = await client.put(
            f"/api/v1/posts/{post_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"base_content": "Corrected Grammatical Draft Content"}
        )
        assert res_update.status_code == 200
        assert res_update.json()["status"] == "draft"
        assert res_update.json()["rejection_reason"] is None

        # 7. Resubmit for approval
        res_resubmit = await client.post(
            f"/api/v1/posts/{post_id}/submit-for-approval",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_resubmit.status_code == 200
        assert res_resubmit.json()["status"] == "pending_approval"

        # 8. Approve post
        res_approve = await client.post(
            f"/api/v1/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"
        assert res_approve.json()["approved_by"] == approval_test_setup["user_a"].id
