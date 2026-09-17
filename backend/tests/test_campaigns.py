import uuid
import pytest
import httpx
from datetime import datetime, timedelta, timezone
from app.main import app


@pytest.mark.asyncio
async def test_campaign_full_lifecycle_and_isolation():
    uid = uuid.uuid4().hex[:8]
    email_a = f"camp_owner_{uid}@example.com"
    email_b = f"camp_outsider_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Register User A (Owner of Team A)
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Campaign Owner"
        })
        assert reg_a.status_code == 201
        
        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "Password123!"
        })
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create Team A
        team_resp = await client.post(
            "/api/v1/teams",
            headers=headers_a,
            json={"name": "Campaign Test Team", "description": "Team for testing campaigns"}
        )
        assert team_resp.status_code == 201
        team_id = team_resp.json()["id"]

        # 2. Register User B (Outsider)
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Campaign Outsider"
        })
        assert reg_b.status_code == 201

        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "Password123!"
        })
        assert login_b.status_code == 200
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Create Campaign as User A
        start_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        end_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()

        create_payload = {
            "name": "Summer Launch 2026",
            "description": "Multi-channel summer product launch campaign",
            "objective": "Brand Awareness & Lead Generation",
            "target_platforms": ["instagram", "facebook", "twitter"],
            "start_date": start_date,
            "end_date": end_date,
            "budget": 5000.0,
            "status": "active"
        }

        camp_create_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers_a,
            json=create_payload
        )
        assert camp_create_resp.status_code == 201, camp_create_resp.text
        campaign_data = camp_create_resp.json()
        campaign_id = campaign_data["id"]
        assert campaign_data["name"] == "Summer Launch 2026"
        assert campaign_data["team_id"] == team_id
        assert campaign_data["status"] == "active"

        # 4. User B (Outsider) cannot list or get Team A's campaign
        list_b = await client.get(f"/api/v1/campaigns?team_id={team_id}", headers=headers_b)
        assert list_b.status_code == 403

        get_b = await client.get(f"/api/v1/campaigns/{campaign_id}?team_id={team_id}", headers=headers_b)
        assert get_b.status_code == 403

        # 5. User A can list and get campaign details
        list_a = await client.get(f"/api/v1/campaigns?team_id={team_id}", headers=headers_a)
        assert list_a.status_code == 200
        assert list_a.json()["total"] >= 1

        get_a = await client.get(f"/api/v1/campaigns/{campaign_id}?team_id={team_id}", headers=headers_a)
        assert get_a.status_code == 200
        assert get_a.json()["id"] == campaign_id

        # 6. Update Campaign
        update_resp = await client.put(
            f"/api/v1/campaigns/{campaign_id}?team_id={team_id}",
            headers=headers_a,
            json={"budget": 7500.0, "status": "paused"}
        )
        assert update_resp.status_code == 200, update_resp.text
        assert update_resp.json()["budget"] == 7500.0
        assert update_resp.json()["status"] == "paused"

        # 7. Create Post linked to Campaign
        post_resp = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "title": "Summer Promo Teaser",
                "base_content": "Get ready for the biggest summer deals!",
                "team_id": team_id,
                "campaign_id": campaign_id,
                "target_platforms": ["instagram"],
                "target_accounts": []
            }
        )
        assert post_resp.status_code == 201, post_resp.text
        print("POST RESP JSON:", post_resp.json())
        assert post_resp.json().get("campaign_id") == campaign_id

        # Verify campaign post count increases
        get_after_post = await client.get(f"/api/v1/campaigns/{campaign_id}?team_id={team_id}", headers=headers_a)
        assert get_after_post.status_code == 200, get_after_post.text
        assert get_after_post.json()["post_count"] == 1

        # Fetch campaign posts endpoint
        camp_posts = await client.get(f"/api/v1/campaigns/{campaign_id}/posts?team_id={team_id}", headers=headers_a)
        assert camp_posts.status_code == 200, camp_posts.text
        assert camp_posts.json()["total"] >= 1

        # 8. Delete Campaign
        del_resp = await client.delete(f"/api/v1/campaigns/{campaign_id}?team_id={team_id}", headers=headers_a)
        assert del_resp.status_code == 200, del_resp.text

        # Verify campaign is gone
        get_deleted = await client.get(f"/api/v1/campaigns/{campaign_id}?team_id={team_id}", headers=headers_a)
        assert get_deleted.status_code == 404


@pytest.mark.asyncio
async def test_campaign_invalid_date_validation():
    uid = uuid.uuid4().hex[:8]
    email = f"camp_val_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        reg = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Campaign Validation User"
        })
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        team_id = (await client.post("/api/v1/teams", headers=headers, json={"name": "Val Team"})).json()["id"]

        # Invalid dates (start after end)
        bad_start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        bad_end = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        bad_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers,
            json={
                "name": "Invalid Date Campaign",
                "start_date": bad_start,
                "end_date": bad_end
            }
        )
        assert bad_resp.status_code == 422


@pytest.mark.asyncio
async def test_cross_team_campaign_post_protection_and_unlinking():
    uid = uuid.uuid4().hex[:8]
    email_a = f"camp_prot_a_{uid}@example.com"
    email_b = f"camp_prot_b_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Register User A & Team A
        await client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "User A"})
        token_a = (await client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"})).json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        team_a_id = (await client.post("/api/v1/teams", headers=headers_a, json={"name": "Team A"})).json()["id"]

        # Register User B & Team B
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "User B"})
        token_b = (await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"})).json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        team_b_id = (await client.post("/api/v1/teams", headers=headers_b, json={"name": "Team B"})).json()["id"]

        # Create Campaign B under Team B
        camp_b_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_b_id}",
            headers=headers_b,
            json={"name": "Campaign B"}
        )
        camp_b_id = camp_b_resp.json()["id"]

        # Create Campaign A under Team A
        camp_a_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_a_id}",
            headers=headers_a,
            json={"name": "Campaign A"}
        )
        camp_a_id = camp_a_resp.json()["id"]

        # 1. Try attaching Team B's campaign to Team A's post -> MUST FAIL (400 Bad Request)
        bad_post = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "title": "Cross-tenant Post Attempt",
                "base_content": "Testing campaign protection",
                "team_id": team_a_id,
                "campaign_id": camp_b_id,
                "target_platforms": ["facebook"]
            }
        )
        assert bad_post.status_code == 400
        assert "does not belong to team" in bad_post.text

        # 2. Create valid Post linked to Campaign A
        valid_post = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "title": "Valid Campaign A Post",
                "base_content": "Belongs to Campaign A",
                "team_id": team_a_id,
                "campaign_id": camp_a_id,
                "target_platforms": ["facebook"]
            }
        )
        assert valid_post.status_code == 201
        post_id = valid_post.json()["id"]
        assert valid_post.json()["campaign_id"] == camp_a_id

        # 3. Delete Campaign A -> Posts must be safely unlinked, NOT deleted!
        del_a = await client.delete(f"/api/v1/campaigns/{camp_a_id}?team_id={team_a_id}", headers=headers_a)
        assert del_a.status_code == 200

        # 4. Fetch Post after Campaign deletion -> Post still exists in MongoDB, but campaign_id is None
        get_post_after_del = await client.get(f"/api/v1/posts/{post_id}", headers=headers_a)
        assert get_post_after_del.status_code == 200
        assert get_post_after_del.json()["campaign_id"] is None

