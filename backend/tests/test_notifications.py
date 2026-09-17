import uuid
import pytest
import httpx
from app.main import app
from app.db.postgres import SessionLocal
from app.services.notification_service import NotificationService
from app.models.enums import NotificationType


@pytest.mark.asyncio
async def test_notifications_full_lifecycle_and_security():
    uid = uuid.uuid4().hex[:8]
    email_a = f"notif_user_a_{uid}@example.com"
    email_b = f"notif_user_b_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Unauthenticated access -> 401
        unauth_res = await client.get("/api/v1/notifications")
        assert unauth_res.status_code == 401

        # 2. Register User A & User B
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "User A"
        })
        assert reg_a.status_code == 201
        user_a_id = reg_a.json()["id"]

        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "Password123!"
        })
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "User B"
        })
        assert reg_b.status_code == 201

        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "Password123!"
        })
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Create notifications directly via NotificationService for User A
        db = SessionLocal()
        try:
            n1 = NotificationService.create_notification(
                db=db,
                user_id=user_a_id,
                type=NotificationType.SYSTEM,
                title="Welcome to SocialPilot",
                message="Your account has been activated."
            )
            n2 = NotificationService.create_notification(
                db=db,
                user_id=user_a_id,
                type=NotificationType.TEAM_INVITATION,
                title="Team Invite",
                message="You have been invited to Join Team Alpha.",
                link="/invite/test123"
            )
            n3 = NotificationService.create_notification(
                db=db,
                user_id=user_a_id,
                type=NotificationType.POST_APPROVED,
                title="Post Approved",
                message="Your post was approved."
            )
            assert n1 is not None and n2 is not None and n3 is not None
            notif_a_id = n1.id
        finally:
            db.close()

        # 4. Query unread count for User A -> Should be 3
        count_res_a = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
        assert count_res_a.status_code == 200
        assert count_res_a.json()["count"] == 3

        # 5. Query unread count for User B -> Should be 0
        count_res_b = await client.get("/api/v1/notifications/unread-count", headers=headers_b)
        assert count_res_b.status_code == 200
        assert count_res_b.json()["count"] == 0

        # 6. List User A notifications with pagination
        list_res_a = await client.get("/api/v1/notifications?page=1&limit=2", headers=headers_a)
        assert list_res_a.status_code == 200
        data_a = list_res_a.json()
        assert data_a["total"] == 3
        assert data_a["unread_count"] == 3
        assert len(data_a["items"]) == 2
        assert data_a["total_pages"] == 2

        # 7. User B attempts to mark User A's notification as read -> MUST return 404 (Not Found for User B)
        stolen_read = await client.patch(f"/api/v1/notifications/{notif_a_id}/read", headers=headers_b)
        assert stolen_read.status_code == 404

        # 8. User A marks one notification as read
        read_res = await client.patch(f"/api/v1/notifications/{notif_a_id}/read", headers=headers_a)
        assert read_res.status_code == 200
        assert read_res.json()["is_read"] is True

        # Unread count should now be 2
        count_res_a2 = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
        assert count_res_a2.json()["count"] == 2

        # 9. Test unread filtering
        unread_only = await client.get("/api/v1/notifications?unread=true", headers=headers_a)
        assert unread_only.status_code == 200
        assert unread_only.json()["total"] == 2

        read_only = await client.get("/api/v1/notifications?unread=false", headers=headers_a)
        assert read_only.status_code == 200
        assert read_only.json()["total"] == 1

        # 10. User A marks all as read
        mark_all_res = await client.patch("/api/v1/notifications/read-all", headers=headers_a)
        assert mark_all_res.status_code == 200
        assert mark_all_res.json()["count"] == 2

        # Unread count should now be 0
        count_res_a3 = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
        assert count_res_a3.json()["count"] == 0


@pytest.mark.asyncio
async def test_notifications_real_event_integration():
    uid = uuid.uuid4().hex[:8]
    email_owner = f"owner_event_{uid}@example.com"
    email_member = f"member_event_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Register owner & member
        reg_o = await client.post("/api/v1/auth/register", json={
            "email": email_owner,
            "password": "Password123!",
            "full_name": "Team Owner"
        })
        reg_m = await client.post("/api/v1/auth/register", json={
            "email": email_member,
            "password": "Password123!",
            "full_name": "Team Member"
        })
        member_id = reg_m.json()["id"]

        login_o = await client.post("/api/v1/auth/login", json={
            "email": email_owner,
            "password": "Password123!"
        })
        login_m = await client.post("/api/v1/auth/login", json={
            "email": email_member,
            "password": "Password123!"
        })

        headers_o = {"Authorization": f"Bearer {login_o.json()['access_token']}"}
        headers_m = {"Authorization": f"Bearer {login_m.json()['access_token']}"}

        # Create Team
        team_res = await client.post("/api/v1/teams", headers=headers_o, json={"name": "Event Test Team"})
        team_id = team_res.json()["id"]

        # Add member -> Triggers TEAM_MEMBER_ADDED notification for member
        add_res = await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers=headers_o,
            json={"email": email_member, "role": "content_creator"}
        )
        assert add_res.status_code == 201

        # Verify member received in-app notification
        m_notifs = await client.get("/api/v1/notifications", headers=headers_m)
        assert m_notifs.status_code == 200
        items_m = m_notifs.json()["items"]
        assert len(items_m) == 1
        assert items_m[0]["type"] == NotificationType.TEAM_MEMBER_ADDED.value
        assert "Event Test Team" in items_m[0]["message"]

        # Update member role -> Triggers ROLE_CHANGED notification for member
        role_res = await client.put(
            f"/api/v1/teams/{team_id}/members/{member_id}",
            headers=headers_o,
            json={"role": "marketing_team"}
        )
        assert role_res.status_code == 200

        m_notifs2 = await client.get("/api/v1/notifications", headers=headers_m)
        assert m_notifs2.json()["total"] == 2
        latest_notif = m_notifs2.json()["items"][0]
        assert latest_notif["type"] == NotificationType.ROLE_CHANGED.value

        # Create campaign -> Triggers CAMPAIGN_CREATED notification for member
        camp_res = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers_o,
            json={"name": "Launch Campaign", "target_platforms": ["instagram"]}
        )
        assert camp_res.status_code == 201

        m_notifs3 = await client.get("/api/v1/notifications", headers=headers_m)
        assert m_notifs3.json()["total"] == 3
        camp_notif = m_notifs3.json()["items"][0]
        assert camp_notif["type"] == NotificationType.CAMPAIGN_CREATED.value
