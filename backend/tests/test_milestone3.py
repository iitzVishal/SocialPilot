import uuid
import pytest
import httpx
from datetime import datetime, timedelta, timezone
from app.main import app
from app.db.mongo import get_mongo_db
from app.core.config import settings


@pytest.mark.asyncio
async def test_milestone3_complete_workflow():
    uid = uuid.uuid4().hex[:8]
    email_a = f"m3_owner_{uid}@example.com"
    email_b = f"m3_outsider_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # =====================================================================
        # 1. SETUP: USERS, TEAMS & AUTH
        # =====================================================================
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Milestone3 Owner"
        })
        assert reg_a.status_code == 201

        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "Password123!"
        })
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        team_a_resp = await client.post(
            "/api/v1/teams",
            headers=headers_a,
            json={"name": "M3 Production Team", "description": "Workspace for Milestone 3 verification"}
        )
        assert team_a_resp.status_code == 201
        team_id = team_a_resp.json()["id"]

        # Outsider user
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "M3 Outsider"
        })
        assert reg_b.status_code == 201

        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "Password123!"
        })
        assert login_b.status_code == 200
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # =====================================================================
        # 2. CAMPAIGN MANAGEMENT: CREATE, READ, UPDATE, REVENUE, FILTER
        # =====================================================================
        start_dt = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        end_dt = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        # Campaign 1: Brand Awareness with Budget and Revenue
        camp1_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers_a,
            json={
                "name": "Summer Product Launch 2026",
                "description": "Multi-platform brand awareness and lead gen",
                "objective": "Lead Generation & Direct Sales",
                "target_platforms": ["instagram", "facebook", "twitter"],
                "start_date": start_dt,
                "end_date": end_dt,
                "budget": 2000.0,
                "revenue": 5500.0,
                "status": "active"
            }
        )
        assert camp1_resp.status_code == 201, camp1_resp.text
        camp1 = camp1_resp.json()
        camp1_id = camp1["id"]
        assert camp1["name"] == "Summer Product Launch 2026"
        assert camp1["budget"] == 2000.0
        assert camp1["revenue"] == 5500.0
        assert camp1["team_id"] == team_id

        # Campaign 2: Retargeting Campaign
        camp2_resp = await client.post(
            f"/api/v1/campaigns?team_id={team_id}",
            headers=headers_a,
            json={
                "name": "Q3 Retargeting Blitz",
                "description": "Retargeting engaged customers",
                "objective": "Direct Sales",
                "target_platforms": ["facebook", "linkedin"],
                "start_date": start_dt,
                "end_date": end_dt,
                "budget": 1000.0,
                "revenue": 3200.0,
                "status": "active"
            }
        )
        assert camp2_resp.status_code == 201
        camp2 = camp2_resp.json()
        camp2_id = camp2["id"]

        # Update Campaign 1 details
        update_resp = await client.put(
            f"/api/v1/campaigns/{camp1_id}?team_id={team_id}",
            headers=headers_a,
            json={
                "name": "Summer Product Launch 2026 — Expanded",
                "revenue": 6000.0
            }
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Summer Product Launch 2026 — Expanded"
        assert update_resp.json()["revenue"] == 6000.0

        # Team isolation: Outsider cannot access campaigns
        out_get = await client.get(f"/api/v1/campaigns/{camp1_id}?team_id={team_id}", headers=headers_b)
        assert out_get.status_code == 403

        # List campaigns with status filter
        list_resp = await client.get(f"/api/v1/campaigns?team_id={team_id}&status=active", headers=headers_a)
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 2

        # =====================================================================
        # 3. CAMPAIGN ↔ POST INTEGRATION
        # =====================================================================
        # Connect a mock social account for posting
        acc_resp = await client.post(
            "/api/v1/accounts",
            headers=headers_a,
            json={
                "platform": "facebook",
                "account_identifier": f"fb_page_{uid}",
                "account_name": "Test Company Page",
                "access_token": "mock_secret_token_fb_12345",
                "team_id": team_id
            }
        )
        assert acc_resp.status_code == 201, acc_resp.text
        account_id = acc_resp.json()["id"]

        # Create Post linked to Campaign 1
        post_resp = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "title": "Summer Special Offer #1",
                "base_content": "Get 25% off our new line this summer! Link in bio.",
                "target_platforms": ["facebook"],
                "target_accounts": [account_id],
                "campaign_id": camp1_id,
                "team_id": team_id
            }
        )
        assert post_resp.status_code == 201, post_resp.text
        post_data = post_resp.json()
        post_id = post_data["id"]
        assert post_data["campaign_id"] == camp1_id

        # Verify post retrieval via Campaign Posts endpoint
        camp_posts = await client.get(f"/api/v1/campaigns/{camp1_id}/posts?team_id={team_id}", headers=headers_a)
        assert camp_posts.status_code == 200
        assert camp_posts.json()["total"] >= 1
        assert any(p["id"] == post_id for p in camp_posts.json()["items"])

        # Verify posts filter by campaign_id query param
        filtered_posts = await client.get(f"/api/v1/posts?team_id={team_id}&campaign_id={camp1_id}", headers=headers_a)
        assert filtered_posts.status_code == 200
        assert filtered_posts.json()["total"] >= 1

        # Cross-team association prevention: User B cannot associate Post with Team A's Campaign
        cross_post = await client.post(
            "/api/v1/posts",
            headers=headers_b,
            json={
                "base_content": "Sneaky cross-team post",
                "campaign_id": camp1_id
            }
        )
        assert cross_post.status_code in (400, 403, 404)

        # Create a second standalone post in team
        post2_resp = await client.post(
            "/api/v1/posts",
            headers=headers_a,
            json={
                "title": "Summer Special Offer #2",
                "base_content": "Standalone offer to be attached",
                "target_platforms": ["facebook"],
                "target_accounts": [account_id],
                "team_id": team_id
            }
        )
        assert post2_resp.status_code == 201
        post2_id = post2_resp.json()["id"]

        # Explicitly attach post2 to Campaign 1
        attach_res = await client.post(
            f"/api/v1/campaigns/{camp1_id}/posts/{post2_id}?team_id={team_id}",
            headers=headers_a
        )
        assert attach_res.status_code == 200
        assert attach_res.json()["post_id"] == post2_id
        assert attach_res.json()["campaign_id"] == camp1_id

        # Outsider (User B) cannot attach posts to Team A's Campaign
        attach_out = await client.post(
            f"/api/v1/campaigns/{camp1_id}/posts/{post2_id}?team_id={team_id}",
            headers=headers_b
        )
        assert attach_out.status_code == 403

        # Explicitly detach post2 from Campaign 1
        detach_res = await client.delete(
            f"/api/v1/campaigns/{camp1_id}/posts/{post2_id}?team_id={team_id}",
            headers=headers_a
        )
        assert detach_res.status_code == 200

        # Detaching a non-associated post returns 400
        detach_repeat = await client.delete(
            f"/api/v1/campaigns/{camp1_id}/posts/{post2_id}?team_id={team_id}",
            headers=headers_a
        )
        assert detach_repeat.status_code == 400

        # =====================================================================
        # 4. ANALYTICS INGESTION & NORMALIZATION (MONGODB)
        # =====================================================================
        mongo_db = get_mongo_db()

        now = datetime.now(timezone.utc)
        # Record post metric snapshot (simulating ingested metrics from platform adapter)
        metric_doc = {
            "post_id": post_id,
            "account_id": account_id,
            "campaign_id": camp1_id,
            "team_id": team_id,
            "platform": "facebook",
            "impressions": 15000,
            "reach": 12000,
            "engagements": 950,
            "likes": 650,
            "comments": 180,
            "shares": 120,
            "clicks": 450,
            "engagement_rate": round((950 / 15000) * 100, 2),
            "recorded_at": now,
            "timestamp": now,
            "raw_payload": {"id": "fb_12345", "post_impressions": 15000}
        }
        await mongo_db["post_analytics"].insert_one(metric_doc)

        # Record account audience snapshot
        account_doc = {
            "account_id": account_id,
            "team_id": team_id,
            "platform": "facebook",
            "follower_count": 25400,
            "net_follower_growth": 450,
            "recorded_at": now,
            "timestamp": now,
            "raw_payload": {"fan_count": 25400}
        }
        await mongo_db["account_analytics"].insert_one(account_doc)

        # Test sync endpoint trigger
        sync_resp = await client.post(f"/api/v1/analytics/sync?team_id={team_id}", headers=headers_a)
        assert sync_resp.status_code == 200
        assert sync_resp.json()["status"] == "completed"

        # =====================================================================
        # 5. ENGAGEMENT ANALYTICS API
        # =====================================================================
        eng_resp = await client.get(f"/api/v1/analytics/engagement?team_id={team_id}&days=30", headers=headers_a)
        assert eng_resp.status_code == 200, eng_resp.text
        eng_data = eng_resp.json()
        assert eng_data["summary"]["impressions"] >= 15000
        assert eng_data["summary"]["reach"] >= 12000
        assert eng_data["summary"]["likes"] >= 650
        assert eng_data["summary"]["comments"] >= 180
        assert eng_data["summary"]["shares"] >= 120
        assert eng_data["summary"]["clicks"] >= 450
        assert eng_data["summary"]["engagement_rate"] > 0
        assert any(p["platform"] == "facebook" for p in eng_data["platform_breakdown"])
        fb_plat = next(p for p in eng_data["platform_breakdown"] if p["platform"] == "facebook")
        assert fb_plat["impressions"] >= 15000

        # Filter by platform
        eng_fb_resp = await client.get(f"/api/v1/analytics/engagement?team_id={team_id}&platform=facebook", headers=headers_a)
        assert eng_fb_resp.status_code == 200
        assert eng_fb_resp.json()["summary"]["impressions"] >= 15000

        # Filter by campaign
        eng_camp_resp = await client.get(f"/api/v1/analytics/engagement?team_id={team_id}&campaign_id={camp1_id}", headers=headers_a)
        assert eng_camp_resp.status_code == 200
        assert eng_camp_resp.json()["summary"]["impressions"] >= 15000

        # =====================================================================
        # 6. AUDIENCE GROWTH ANALYTICS API
        # =====================================================================
        aud_resp = await client.get(f"/api/v1/analytics/audience?team_id={team_id}&days=30", headers=headers_a)
        assert aud_resp.status_code == 200, aud_resp.text
        aud_data = aud_resp.json()
        assert aud_data["total_followers"] >= 25400
        assert len(aud_data["accounts"]) >= 1
        fb_acc = next((a for a in aud_data["accounts"] if a["account_id"] == account_id), None)
        assert fb_acc is not None
        assert fb_acc["follower_count"] == 25400

        # =====================================================================
        # 7. ROI ANALYTICS API & FORMULA VERIFICATION
        # =====================================================================
        roi_resp = await client.get(f"/api/v1/analytics/roi?team_id={team_id}&days=30", headers=headers_a)
        assert roi_resp.status_code == 200, roi_resp.text
        roi_data = roi_resp.json()
        assert roi_data["total_budget"] >= 3000.0  # camp1 (2000) + camp2 (1000)
        assert roi_data["total_revenue"] >= 9200.0  # camp1 (6000) + camp2 (3200)

        # Expected overall ROI: ((9200 - 3000) / 3000) * 100 = 206.67%
        expected_roi = ((roi_data["total_revenue"] - roi_data["total_budget"]) / roi_data["total_budget"]) * 100
        assert abs(roi_data["overall_roi_percentage"] - round(expected_roi, 2)) < 0.1

        # Campaign 1 specific ROI & cost efficiency checks
        camp1_roi_item = next((c for c in roi_data["campaigns"] if c["campaign_id"] == camp1_id), None)
        assert camp1_roi_item is not None
        assert camp1_roi_item["budget"] == 2000.0
        assert camp1_roi_item["revenue"] == 6000.0
        # ROI % = ((6000 - 2000) / 2000) * 100 = 200.0%
        assert camp1_roi_item["roi_percentage"] == 200.0
        # CPE = 2000 / total_engagements (1400) = 1.43
        assert camp1_roi_item["cost_per_engagement"] is not None
        assert abs(camp1_roi_item["cost_per_engagement"] - round(2000.0 / camp1_roi_item["total_engagements"], 2)) < 0.1
        # CPC = 2000 / 450 = 4.44
        assert camp1_roi_item["cost_per_click"] is not None
        assert abs(camp1_roi_item["cost_per_click"] - round(2000.0 / 450, 2)) < 0.1

        # =====================================================================
        # 8. CAMPAIGN ANALYTICS ENDPOINT (SINGLE CAMPAIGN)
        # =====================================================================
        single_camp_analytics = await client.get(
            f"/api/v1/campaigns/{camp1_id}/analytics?team_id={team_id}",
            headers=headers_a
        )
        assert single_camp_analytics.status_code == 200
        sca = single_camp_analytics.json()
        assert sca["campaign_id"] == camp1_id
        assert sca["engagement"]["impressions"] >= 15000
        assert sca["engagement"]["reach"] >= 12000
        assert sca["engagement"]["total_engagements"] >= 950
        assert sca["budget"] == 2000.0
        assert sca["revenue"] == 6000.0
        assert sca["roi"]["roi_percentage"] == 200.0

        # =====================================================================
        # 9. CAMPAIGN COMPARISON API
        # =====================================================================
        # POST /campaigns/compare
        comp_post = await client.post(
            f"/api/v1/campaigns/compare?team_id={team_id}",
            headers=headers_a,
            json={"campaign_ids": [camp1_id, camp2_id]}
        )
        assert comp_post.status_code == 200, comp_post.text
        comp_data = comp_post.json()
        assert len(comp_data["campaigns"]) == 2

        comp_names = [c["name"] for c in comp_data["campaigns"]]
        assert "Summer Product Launch 2026 — Expanded" in comp_names
        assert "Q3 Retargeting Blitz" in comp_names

        # GET /campaigns/compare?campaign_ids=id1,id2
        comp_get = await client.get(
            f"/api/v1/campaigns/compare?team_id={team_id}&campaign_ids={camp1_id},{camp2_id}",
            headers=headers_a
        )
        assert comp_get.status_code == 200
        assert len(comp_get.json()["campaigns"]) == 2

        # Cross-team comparison forbidden
        comp_out = await client.post(
            f"/api/v1/campaigns/compare?team_id={team_id}",
            headers=headers_b,
            json={"campaign_ids": [camp1_id, camp2_id]}
        )
        assert comp_out.status_code == 403

        # =====================================================================
        # 10. REPORTING & EXPORT (PDF & EXCEL)
        # =====================================================================
        # Campaign PDF Report
        pdf_resp = await client.get(
            f"/api/v1/reports/campaign/{camp1_id}/pdf?team_id={team_id}",
            headers=headers_a
        )
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert len(pdf_resp.content) > 100
        assert pdf_resp.content[:4] == b"%PDF"

        # Campaign Excel Report
        excel_resp = await client.get(
            f"/api/v1/reports/campaign/{camp1_id}/excel?team_id={team_id}",
            headers=headers_a
        )
        assert excel_resp.status_code == 200
        assert "spreadsheetml" in excel_resp.headers["content-type"] or "excel" in excel_resp.headers["content-type"]
        assert len(excel_resp.content) > 100

        # Workspace General Reports (PDF & Excel)
        ws_pdf = await client.get(f"/api/v1/reports/pdf?team_id={team_id}&days=30", headers=headers_a)
        assert ws_pdf.status_code == 200
        assert ws_pdf.content[:4] == b"%PDF"

        ws_excel = await client.get(f"/api/v1/reports/excel?team_id={team_id}&days=30", headers=headers_a)
        assert ws_excel.status_code == 200
        assert len(ws_excel.content) > 100

        # Outsider cannot download Team A reports
        out_pdf = await client.get(
            f"/api/v1/reports/campaign/{camp1_id}/pdf?team_id={team_id}",
            headers=headers_b
        )
        assert out_pdf.status_code == 403

        # =====================================================================
        # 11. SECURITY & RBAC AUDIT
        # =====================================================================
        # Unauthenticated calls rejected
        unauth_eng = await client.get(f"/api/v1/analytics/engagement?team_id={team_id}")
        assert unauth_eng.status_code == 401

        unauth_comp = await client.post(f"/api/v1/campaigns/compare?team_id={team_id}", json={"campaign_ids": [camp1_id]})
        assert unauth_comp.status_code == 401

        unauth_pdf = await client.get(f"/api/v1/reports/campaign/{camp1_id}/pdf?team_id={team_id}")
        assert unauth_pdf.status_code == 401

        # Delete campaign lifecycle
        del_resp = await client.delete(f"/api/v1/campaigns/{camp2_id}?team_id={team_id}", headers=headers_a)
        assert del_resp.status_code == 200
