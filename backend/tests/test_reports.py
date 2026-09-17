import io
import uuid
import pytest
import httpx
import openpyxl
from app.main import app
from app.db.postgres import SessionLocal
from app.db.mongo import get_mongo_db
from app.models.enums import NotificationType


@pytest.mark.asyncio
async def test_reports_unauthenticated_and_validation_errors():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Unauthenticated PDF request -> 401
        res_pdf_unauth = await client.get("/api/v1/reports/pdf?team_id=1&days=30")
        assert res_pdf_unauth.status_code == 401

        # 2. Unauthenticated Excel request -> 401
        res_excel_unauth = await client.get("/api/v1/reports/excel?team_id=1&days=30")
        assert res_excel_unauth.status_code == 401

        # Register User
        uid = uuid.uuid4().hex[:8]
        reg = await client.post("/api/v1/auth/register", json={
            "email": f"report_val_{uid}@example.com",
            "password": "Password123!",
            "full_name": "Report Validation User"
        })
        assert reg.status_code == 201

        login = await client.post("/api/v1/auth/login", json={
            "email": f"report_val_{uid}@example.com",
            "password": "Password123!"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Create Team
        team_res = await client.post("/api/v1/teams", headers=headers, json={"name": f"Val Team {uid}"})
        team_id = team_res.json()["id"]

        # 3. Invalid days (0, -5, 999) -> 400 Bad Request
        res_days_zero = await client.get(f"/api/v1/reports/pdf?team_id={team_id}&days=0", headers=headers)
        assert res_days_zero.status_code == 422 or res_days_zero.status_code == 400

        res_days_over = await client.get(f"/api/v1/reports/excel?team_id={team_id}&days=999", headers=headers)
        assert res_days_over.status_code == 422 or res_days_over.status_code == 400


@pytest.mark.asyncio
async def test_reports_team_isolation_and_security():
    uid = uuid.uuid4().hex[:8]
    email_a = f"report_owner_a_{uid}@example.com"
    email_b = f"report_outsider_b_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Register Owner A and Outsider B
        await client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "Owner A"})
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "Outsider B"})

        login_a = await client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"})

        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # Owner A creates Team A
        team_res = await client.post("/api/v1/teams", headers=headers_a, json={"name": "Team Alpha Security"})
        team_id = team_res.json()["id"]

        # Outsider B attempts to access Team A's PDF report -> 403 Forbidden
        pdf_stolen = await client.get(f"/api/v1/reports/pdf?team_id={team_id}&days=30", headers=headers_b)
        assert pdf_stolen.status_code == 403

        # Outsider B attempts to access Team A's Excel report -> 403 Forbidden
        excel_stolen = await client.get(f"/api/v1/reports/excel?team_id={team_id}&days=30", headers=headers_b)
        assert excel_stolen.status_code == 403


@pytest.mark.asyncio
async def test_authorized_pdf_and_excel_generation_and_content_inspection():
    uid = uuid.uuid4().hex[:8]
    email = f"report_gen_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Register user and login
        await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Report Gen User"})
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Create Team
        team_res = await client.post("/api/v1/teams", headers=headers, json={"name": "Report Test Workspace"})
        team_id = team_res.json()["id"]

        # Insert a post directly into MongoDB for the team
        db = SessionLocal()
        try:
            mongo_db = get_mongo_db()
            posts_coll = mongo_db["posts"]
            from datetime import datetime, timezone
            await posts_coll.insert_one({
                "team_id": team_id,
                "user_id": 1,
                "title": "Test Title",
                "content": "Test report post content for export inspection",
                "base_content": "Test report post content for export inspection",
                "status": "draft",
                "target_platforms": ["twitter", "linkedin"],
                "created_at": datetime.now(timezone.utc),
            })
        finally:
            db.close()

        # Create a campaign in team
        camp_res = await client.post(f"/api/v1/campaigns?team_id={team_id}", headers=headers, json={
            "name": "Summer Blast Campaign",
            "target_platforms": ["twitter"]
        })
        assert camp_res.status_code == 201

        # -------------------------------------------------------------
        # 1. TEST PDF REPORT GENERATION & CONTENT
        # -------------------------------------------------------------
        pdf_res = await client.get(f"/api/v1/reports/pdf?team_id={team_id}&days=30", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in pdf_res.headers
        assert f"socialpilot_report_team_{team_id}_30d.pdf" in pdf_res.headers["Content-Disposition"]

        pdf_bytes = pdf_res.content
        assert len(pdf_bytes) > 500
        # Valid PDF header magic bytes
        assert pdf_bytes.startswith(b"%PDF")

        # PDF text inspection using pypdf
        import pypdf
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) >= 1
        pdf_extracted_text = "".join([page.extract_text() for page in pdf_reader.pages])

        assert "SocialPilot Workspace Report" in pdf_extracted_text
        assert "Report Test Workspace" in pdf_extracted_text
        assert "Executive Summary" in pdf_extracted_text
        assert "Connected Social Accounts" in pdf_extracted_text
        assert "External Platform Engagement" in pdf_extracted_text

        # Verify secret audit safeguard
        assert "access_token" not in pdf_extracted_text
        assert "client_secret" not in pdf_extracted_text
        assert "Password123!" not in pdf_extracted_text

        # -------------------------------------------------------------
        # 2. TEST EXCEL REPORT GENERATION & CONTENT
        # -------------------------------------------------------------
        excel_res = await client.get(f"/api/v1/reports/excel?team_id={team_id}&days=30", headers=headers)
        assert excel_res.status_code == 200
        assert excel_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "Content-Disposition" in excel_res.headers
        assert f"socialpilot_report_team_{team_id}_30d.xlsx" in excel_res.headers["Content-Disposition"]

        excel_bytes = excel_res.content
        assert len(excel_bytes) > 1000

        # Load workbook with OpenPyXL to inspect sheets and cells
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        sheet_names = wb.sheetnames
        expected_sheets = ["Summary", "Posts", "Platform Breakdown", "Campaigns", "Social Accounts", "Daily Trend"]
        for s in expected_sheets:
            assert s in sheet_names

        # Inspect Summary sheet
        ws_sum = wb["Summary"]
        assert ws_sum.cell(row=1, column=1).value == "SocialPilot Workspace Analytics Summary"
        assert f"Workspace: Report Test Workspace" in ws_sum.cell(row=2, column=1).value

        # Inspect Posts sheet
        ws_posts = wb["Posts"]
        assert ws_posts.cell(row=1, column=1).value == "Post ID"
        assert ws_posts.cell(row=1, column=2).value == "Content"
        # Row 2 should contain the created post
        assert ws_posts.cell(row=2, column=2).value == "Test report post content for export inspection"

        # Inspect Campaigns sheet
        ws_camp = wb["Campaigns"]
        assert ws_camp.cell(row=1, column=2).value == "Campaign Name"
        assert ws_camp.cell(row=2, column=2).value == "Summer Blast Campaign"

        # -------------------------------------------------------------
        # 3. METRIC CONSISTENCY CHECK (Reports vs Analytics API)
        # -------------------------------------------------------------
        analytics_res = await client.get(f"/api/v1/analytics/overview?team_id={team_id}&days=30", headers=headers)
        assert analytics_res.status_code == 200
        analytics_data = analytics_res.json()

        # Compare total posts count in analytics vs Summary sheet
        # Row 7 is "Period Total Posts"
        summary_metric_row = None
        for r in range(6, 16):
            if ws_sum.cell(row=r, column=1).value == "Period Total Posts":
                summary_metric_row = r
                break
        assert summary_metric_row is not None
        excel_period_total = ws_sum.cell(row=summary_metric_row, column=2).value
        assert excel_period_total == analytics_data["posts"]["period_total"]


@pytest.mark.asyncio
async def test_empty_team_report_generation():
    uid = uuid.uuid4().hex[:8]
    email = f"empty_report_{uid}@example.com"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Empty Team User"})
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Create Empty Team
        team_res = await client.post("/api/v1/teams", headers=headers, json={"name": "Empty Team Workspace"})
        team_id = team_res.json()["id"]

        # PDF generation for empty team should succeed without crashing
        pdf_res = await client.get(f"/api/v1/reports/pdf?team_id={team_id}&days=30", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF")

        # Excel generation for empty team should succeed without crashing
        excel_res = await client.get(f"/api/v1/reports/excel?team_id={team_id}&days=30", headers=headers)
        assert excel_res.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(excel_res.content))
        assert "Summary" in wb.sheetnames
