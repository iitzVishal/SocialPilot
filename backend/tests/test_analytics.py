import uuid
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from app.main import app
from app.db.mongo import get_mongo_db


@pytest.mark.asyncio
async def test_analytics_endpoints_and_team_isolation():
    uid = uuid.uuid4().hex[:8]
    email_a = f"analytics_owner_{uid}@example.com"
    email_b = f"analytics_outsider_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Register User A & create Team A
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Analytics Owner"
        })
        assert reg_a.status_code == 201

        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "Password123!"
        })
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        team_resp = await client.post(
            "/api/v1/teams",
            headers=headers_a,
            json={"name": "Analytics Team", "description": "Team for analytics testing"}
        )
        assert team_resp.status_code == 201
        team_id = team_resp.json()["id"]

        # 2. Register User B (Outsider)
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Analytics Outsider"
        })
        assert reg_b.status_code == 201

        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "Password123!"
        })
        assert login_b.status_code == 200
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. User A queries analytics overview (Empty Dataset)
        ov_resp = await client.get(
            f"/api/v1/analytics/overview?team_id={team_id}&days=30",
            headers=headers_a
        )
        assert ov_resp.status_code == 200
        ov_data = ov_resp.json()
        assert ov_data["posts"]["period_total"] == 0
        assert ov_data["posts"]["published"] == 0
        assert ov_data["posts"]["success_rate"] == 0
        assert ov_data["engagement"]["available"] is False

        # 4. User A queries timeline (Empty Dataset)
        tl_resp = await client.get(
            f"/api/v1/analytics/posts/timeline?team_id={team_id}&days=30",
            headers=headers_a
        )
        assert tl_resp.status_code == 200
        tl_data = tl_resp.json()
        assert len(tl_data["series"]) == 30

        # 5. User A queries campaign performance (Empty Dataset)
        cp_resp = await client.get(
            f"/api/v1/analytics/campaigns/performance?team_id={team_id}",
            headers=headers_a
        )
        assert cp_resp.status_code == 200
        cp_data = cp_resp.json()
        assert cp_data["total"] == 0

        # 6. User B (Outsider) attempts to access Team A analytics -> MUST return 403 Forbidden
        denied_ov = await client.get(
            f"/api/v1/analytics/overview?team_id={team_id}&days=30",
            headers=headers_b
        )
        assert denied_ov.status_code == 403
        assert "Access denied" in denied_ov.json()["detail"] or "Forbidden" in denied_ov.json()["detail"]

        denied_tl = await client.get(
            f"/api/v1/analytics/posts/timeline?team_id={team_id}&days=30",
            headers=headers_b
        )
        assert denied_tl.status_code == 403

        denied_cp = await client.get(
            f"/api/v1/analytics/campaigns/performance?team_id={team_id}",
            headers=headers_b
        )
        assert denied_cp.status_code == 403


@pytest.mark.asyncio
async def test_analytics_exact_metrics_and_date_filtering():
    uid = uuid.uuid4().hex[:8]
    email = f"analytics_math_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Register user & create team
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Math Tester"
        })
        login_res = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "Password123!"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        team_res = await client.post("/api/v1/teams", headers=headers, json={"name": "Math Team"})
        team_id = team_res.json()["id"]

        # Create a campaign
        camp_res = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers,
            json={
                "name": "Summer Blast",
                "target_platforms": ["instagram", "facebook"],
                "status": "active"
            }
        )
        assert camp_res.status_code == 201
        campaign_id = camp_res.json()["id"]

        # Insert 5 posts directly into MongoDB for exact calculation testing:
        # - 3 published
        # - 1 scheduled
        # - 1 failed
        # - 1 old post (10 days old)
        mongo_db = get_mongo_db()
        posts_coll = mongo_db["posts"]

        now = datetime.now(timezone.utc)
        post_docs = [
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Pub Post 1",
                "base_content": "Content 1",
                "status": "published",
                "target_platforms": ["instagram", "facebook"],
                "campaign_id": campaign_id,
                "created_at": now - timedelta(days=2),
                "published_at": now - timedelta(days=2),
            },
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Pub Post 2",
                "base_content": "Content 2",
                "status": "published",
                "target_platforms": ["instagram"],
                "campaign_id": campaign_id,
                "created_at": now - timedelta(days=1),
                "published_at": now - timedelta(days=1),
            },
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Pub Post 3",
                "base_content": "Content 3",
                "status": "published",
                "target_platforms": ["linkedin"],
                "campaign_id": None,
                "created_at": now - timedelta(days=5),
                "published_at": now - timedelta(days=5),
            },
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Sched Post",
                "base_content": "Content 4",
                "status": "scheduled",
                "target_platforms": ["twitter"],
                "campaign_id": campaign_id,
                "created_at": now - timedelta(days=3),
                "scheduled_at": now + timedelta(days=2),
            },
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Fail Post",
                "base_content": "Content 5",
                "status": "failed",
                "target_platforms": ["facebook"],
                "campaign_id": campaign_id,
                "created_at": now - timedelta(days=4),
            },
            # 6th post outside 7-day period (10 days old)
            {
                "team_id": team_id,
                "user_id": 1,
                "title": "Old Post",
                "base_content": "Old Content",
                "status": "published",
                "target_platforms": ["instagram"],
                "campaign_id": None,
                "created_at": now - timedelta(days=10),
                "published_at": now - timedelta(days=10),
            },
        ]
        await posts_coll.insert_many(post_docs)

        # Query 7-day overview
        ov7 = await client.get(
            f"/api/v1/analytics/overview?team_id={team_id}&days=7",
            headers=headers
        )
        assert ov7.status_code == 200
        d7 = ov7.json()
        assert d7["posts"]["period_total"] == 5  # 5 posts created in last 7 days
        assert d7["posts"]["published"] == 3
        assert d7["posts"]["scheduled"] == 1
        assert d7["posts"]["failed"] == 1
        assert d7["posts"]["lifetime_total"] == 6  # 6 total posts lifetime
        assert d7["posts"]["lifetime_published"] == 4
        assert d7["posts"]["success_rate"] == 60.0  # 3/5 = 60.0%

        # Query 30-day overview (includes the 10-day-old post)
        ov30 = await client.get(
            f"/api/v1/analytics/overview?team_id={team_id}&days=30",
            headers=headers
        )
        assert ov30.status_code == 200
        d30 = ov30.json()
        assert d30["posts"]["period_total"] == 6
        assert d30["posts"]["published"] == 4

        # Query campaign performance
        cp = await client.get(
            f"/api/v1/analytics/campaigns/performance?team_id={team_id}",
            headers=headers
        )
        assert cp.status_code == 200
        cp_items = cp.json()["campaigns"]
        assert len(cp_items) == 1
        summer_camp = cp_items[0]
        assert summer_camp["name"] == "Summer Blast"
        assert summer_camp["total_posts"] == 4  # 2 published, 1 scheduled, 1 failed
        assert summer_camp["published_posts"] == 2
        assert summer_camp["scheduled_posts"] == 1
        assert summer_camp["failed_posts"] == 1
        assert summer_camp["publish_rate"] == 50.0  # 2/4 = 50.0%

