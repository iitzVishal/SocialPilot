import uuid
import pytest
import httpx
from datetime import datetime, timedelta, timezone
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


@pytest.fixture
def test_setup_invitations():
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User A: Owner of Team A
    user_a = User(
        email=f"owner_a_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Owner A",
        role=UserRole.MARKETING_TEAM,
        is_active=True
    )
    # User B: Standard member (Content Creator) of Team A
    user_b = User(
        email=f"creator_a_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Creator A",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    # User C: Invited user (to Team A)
    user_c = User(
        email=f"invited_c_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Invited C",
        role=UserRole.CONTENT_CREATOR,
        is_active=True
    )
    # User D: Owner of Team B (cross-team check)
    user_d = User(
        email=f"owner_b_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Owner B",
        role=UserRole.MARKETING_TEAM,
        is_active=True
    )
    # User E: System Administrator (SysAdmin)
    user_e = User(
        email=f"sysadmin_{uid}@socialpilot.test",
        hashed_password="hashed_pw_test",
        full_name="Sys Admin",
        role=UserRole.ADMINISTRATOR,
        is_active=True
    )
    session.add_all([user_a, user_b, user_c, user_d, user_e])
    session.commit()

    # Create Team A owned by User A
    team_a = Team(
        name=f"Team A {uid}",
        description="Team A Desc",
        owner_id=user_a.id,
        require_post_approval=False
    )
    # Create Team B owned by User D
    team_b = Team(
        name=f"Team B {uid}",
        description="Team B Desc",
        owner_id=user_d.id,
        require_post_approval=False
    )
    session.add_all([team_a, team_b])
    session.commit()

    # Add memberships
    member_a = TeamMember(team_id=team_a.id, user_id=user_a.id, role=UserRole.ADMINISTRATOR)
    member_b = TeamMember(team_id=team_a.id, user_id=user_b.id, role=UserRole.CONTENT_CREATOR)
    member_d = TeamMember(team_id=team_b.id, user_id=user_d.id, role=UserRole.ADMINISTRATOR)
    session.add_all([member_a, member_b, member_d])
    session.commit()

    token_a = create_access_token(subject=user_a.id)
    token_b = create_access_token(subject=user_b.id)
    token_c = create_access_token(subject=user_c.id)
    token_d = create_access_token(subject=user_d.id)
    token_e = create_access_token(subject=user_e.id)

    yield {
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "user_d": user_d,
        "user_e": user_e,
        "team_a": team_a,
        "team_b": team_b,
        "token_a": token_a,
        "token_b": token_b,
        "token_c": token_c,
        "token_d": token_d,
        "token_e": token_e,
        "uid": uid,
    }

    session.close()


@pytest.mark.anyio
async def test_team_invitations_full_workflow(test_setup_invitations):
    data = test_setup_invitations
    team_a_id = data["team_a"].id
    team_b_id = data["team_b"].id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test Content Creator (User B) cannot invite
        invite_payload = {
            "email": data["user_c"].email,
            "role": "content_creator"
        }
        res = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations",
            json=invite_payload,
            headers={"Authorization": f"Bearer {data['token_b']}"}
        )
        assert res.status_code == 403

        # 2. Test Team Owner (User A) can create invitation
        res = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations",
            json=invite_payload,
            headers={"Authorization": f"Bearer {data['token_a']}"}
        )
        assert res.status_code == 201
        inv_data = res.json()
        assert inv_data["status"] == "pending"
        assert inv_data["email"] == data["user_c"].email
        assert "token" in inv_data
        token = inv_data["token"]

        # 3. Test wrong email cannot accept (User D tries to accept User C's invitation)
        res = await ac.post(
            f"/api/v1/invitations/{token}/accept",
            headers={"Authorization": f"Bearer {data['token_d']}"}
        )
        assert res.status_code == 403
        assert "does not match" in res.json()["detail"].lower()

        # 4. Test wrong token acceptance returns 404
        res = await ac.post(
            f"/api/v1/invitations/invalid_token_123/accept",
            headers={"Authorization": f"Bearer {data['token_c']}"}
        )
        assert res.status_code == 404

        # 5. Test correct email accepts successfully
        res = await ac.post(
            f"/api/v1/invitations/{token}/accept",
            headers={"Authorization": f"Bearer {data['token_c']}"}
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Verify new member record exists
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        member = session.query(TeamMember).filter_by(team_id=team_a_id, user_id=data["user_c"].id).first()
        assert member is not None
        assert member.role == UserRole.CONTENT_CREATOR

        # 6. Test accepted invitation cannot be reused
        res = await ac.post(
            f"/api/v1/invitations/{token}/accept",
            headers={"Authorization": f"Bearer {data['token_c']}"}
        )
        assert res.status_code == 400

        # 7. Test Duplicate Pending Invitation (creating a new one cancels the previous one)
        # Create Invite 1
        res1 = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations",
            json={"email": f"new_user_{data['uid']}@socialpilot.test", "role": "content_creator"},
            headers={"Authorization": f"Bearer {data['token_a']}"}
        )
        token1 = res1.json()["token"]

        # Create Invite 2 for same email
        res2 = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations",
            json={"email": f"new_user_{data['uid']}@socialpilot.test", "role": "content_creator"},
            headers={"Authorization": f"Bearer {data['token_a']}"}
        )
        token2 = res2.json()["token"]

        # Token 1 should be cancelled
        res = await ac.get(f"/api/v1/invitations/{token1}")
        assert res.status_code == 400

        # Token 2 should be active/pending
        res = await ac.get(f"/api/v1/invitations/{token2}")
        assert res.status_code == 200
        assert res.json()["status"] == "pending"

        # 8. Test Cancel Invitation
        invite_to_cancel = res2.json()
        res = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations/{invite_to_cancel['id']}/cancel",
            headers={"Authorization": f"Bearer {data['token_a']}"}
        )
        assert res.status_code == 200

        # Cancelled token cannot be accepted
        res = await ac.post(
            f"/api/v1/invitations/{token2}/accept",
            headers={"Authorization": f"Bearer {data['token_c']}"}
        )
        assert res.status_code == 400

        # 9. Test Reject Invitation
        # Invite again (use a fresh email so they are not already a member)
        reject_email = f"reject_me_{data['uid']}@socialpilot.test"
        # Create a user with this email first so they can accept/reject
        session = Session()
        reject_user = User(
            email=reject_email,
            hashed_password="hashed_pw_test",
            full_name="Reject User",
            role=UserRole.CONTENT_CREATOR,
            is_active=True
        )
        session.add(reject_user)
        session.commit()
        reject_token = create_access_token(subject=reject_user.id)

        res_invite = await ac.post(
            f"/api/v1/teams/{team_a_id}/invitations",
            json={"email": reject_email, "role": "marketing_team"},
            headers={"Authorization": f"Bearer {data['token_a']}"}
        )
        assert res_invite.status_code == 201
        token3 = res_invite.json()["token"]

        res = await ac.post(
            f"/api/v1/invitations/{token3}/reject",
            headers={"Authorization": f"Bearer {reject_token}"}
        )
        assert res.status_code == 200

        # Rejected token cannot be accepted
        res = await ac.post(
            f"/api/v1/invitations/{token3}/accept",
            headers={"Authorization": f"Bearer {reject_token}"}
        )
        assert res.status_code == 400

        # 10. Test System Admin bypass access (User E can list/create invites for Team A)
        res = await ac.get(
            f"/api/v1/teams/{team_a_id}/invitations",
            headers={"Authorization": f"Bearer {data['token_e']}"}
        )
        assert res.status_code == 200
        assert len(res.json()) > 0

        # 11. Test Cross-team Isolation (Owner of Team B trying to access Team A invitations)
        res = await ac.get(
            f"/api/v1/teams/{team_a_id}/invitations",
            headers={"Authorization": f"Bearer {data['token_d']}"}
        )
        assert res.status_code == 403

        session.close()


@pytest.mark.anyio
async def test_invitation_email_notification_delivery(test_setup_invitations):
    from unittest.mock import patch, MagicMock
    from app.tasks.email import send_invitation_email_task
    from app.services.email_service import EmailService

    data = test_setup_invitations
    team_a_id = data["team_a"].id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Mock Celery delay to verify task is queued on invitation creation
        with patch("app.tasks.email.send_invitation_email_task.delay") as mock_delay:
            invite_payload = {
                "email": "test_delivery@socialpilot.test",
                "role": "business_user"
            }
            res = await ac.post(
                f"/api/v1/teams/{team_a_id}/invitations",
                json=invite_payload,
                headers={"Authorization": f"Bearer {data['token_a']}"}
            )
            assert res.status_code == 201
            inv_data = res.json()
            assert inv_data["status"] == "pending"

            # Assert task was queued
            mock_delay.assert_called_once()
            args, kwargs = mock_delay.call_args
            invitation_id = args[0]
            invite_url = args[1]
            assert invitation_id == inv_data["id"]
            assert inv_data["token"] in invite_url

        # Test the actual Celery task execution directly
        with patch.object(EmailService, "send_email", return_value=True) as mock_send_email:
            # Execute task synchronously
            result = send_invitation_email_task(invitation_id, invite_url)
            assert result["status"] == "SENT"

            # Assert EmailService.send_email was called with correct parameters
            mock_send_email.assert_called_once()
            _, kwargs = mock_send_email.call_args
            assert kwargs["to_email"] == "test_delivery@socialpilot.test"
            assert data["team_a"].name in kwargs["subject"]
            assert "Business User" in kwargs["html_content"]
            assert invite_url in kwargs["html_content"]

        # Test email task handles expired or cancelled invitation
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Mark as cancelled
        inv_record = session.query(TeamInvitation).filter_by(id=invitation_id).first()
        inv_record.status = TeamInvitationStatus.CANCELLED
        session.commit()

        result = send_invitation_email_task(invitation_id, invite_url)
        assert "SKIPPED" in result["status"]

        # Test email provider failure does NOT delete the database record
        inv_record = session.query(TeamInvitation).filter_by(id=invitation_id).first()
        inv_record.status = TeamInvitationStatus.PENDING
        session.commit()

        with patch.object(EmailService, "send_email", side_effect=Exception("SMTP Outage")) as mock_fail_send:
            with pytest.raises(Exception):
                send_invitation_email_task(invitation_id, invite_url)
            
            # Record should still exist in database in pending state
            inv_check = session.query(TeamInvitation).filter_by(id=invitation_id).first()
            assert inv_check is not None
            assert inv_check.status == TeamInvitationStatus.PENDING

        session.close()


@pytest.mark.anyio
async def test_resend_email_provider_dispatch():
    from unittest.mock import patch, MagicMock
    from app.services.email_service import EmailService
    from app.core.config import settings

    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch.object(settings, "EMAIL_PROVIDER", "resend"):
            with patch.object(settings, "RESEND_API_KEY", "re_testkey"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_client.post.return_value = mock_response
                    mock_client_class.return_value.__enter__.return_value = mock_client

                    success = EmailService.send_email(
                        to_email="recipient@resend.test",
                        subject="Resend Test Subject",
                        html_content="<p>Test</p>",
                        text_content="Test Plain"
                    )

                    assert success is True
                    mock_client.post.assert_called_once()
                    args, kwargs = mock_client.post.call_args
                    assert args[0] == "https://api.resend.com/emails"
                    assert kwargs["headers"]["Authorization"] == "Bearer re_testkey"
                    assert kwargs["json"]["to"] == "recipient@resend.test"
                    assert kwargs["json"]["html"] == "<p>Test</p>"
                    assert kwargs["json"]["text"] == "Test Plain"

            with patch.object(settings, "RESEND_API_KEY", None):
                with pytest.raises(ValueError) as exc:
                    EmailService.send_email(
                        to_email="recipient@resend.test",
                        subject="Resend Test Subject",
                        html_content="<p>Test</p>"
                    )
                assert "RESEND_API_KEY must be configured" in str(exc.value)


