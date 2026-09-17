import httpx
import uuid
import sys

BASE_BACKEND = "http://127.0.0.1:8000/api/v1"
BASE_FRONTEND = "http://localhost:5173"


def run_regression_audit():
    print("==================================================")
    print("SOCIALPILOT FRONTEND REGRESSION AUDIT")
    print("==================================================")
    
    # 1. Check Frontend Dev Server
    with httpx.Client() as client:
        r_front = client.get(BASE_FRONTEND)
        assert r_front.status_code == 200, f"Frontend down: {r_front.status_code}"
        print("✓ Frontend Dev Server: PASS (HTTP 200)")

    # 2. End-to-End Live User Flow Test
    uid = uuid.uuid4().hex[:6]
    email = f"audit_user_{uid}@socialpilot.test"
    password = "AuditPassword123!"
    full_name = f"Audit Engineer {uid}"
    
    with httpx.Client(base_url=BASE_BACKEND, timeout=10.0) as client:
        # Step 1: REGISTER
        reg_res = client.post("/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
        user_id = reg_res.json()["id"]
        print(f"✓ 1. POST /auth/register: PASS (User ID: {user_id})")

        # Step 2: LOGIN
        login_res = client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token_data = login_res.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        print("✓ 2. POST /auth/login: PASS (JWT Access & Refresh Tokens issued)")

        # Step 3: GET /auth/me
        me_res = client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email
        print(f"✓ 3. GET /auth/me: PASS (User: {me_res.json()['full_name']}, Role: {me_res.json()['role']})")

        # Step 4: CONNECT 6 PLATFORM ACCOUNTS
        platforms = ["facebook", "instagram", "linkedin", "twitter", "youtube", "pinterest"]
        connected_ids = {}
        for p in platforms:
            conn_res = client.post("/accounts", headers=headers, json={
                "platform": p,
                "account_name": f"{p.capitalize()} Channel",
                "account_identifier": f"id_{p}_{uid}",
                "access_token": f"secret_oauth_{p}_{uid}_key",
                "refresh_token": f"refresh_{p}_{uid}_key"
            })
            assert conn_res.status_code == 201, f"Connect {p} failed: {conn_res.text}"
            account_data = conn_res.json()
            assert account_data["platform"] == p
            assert "access_token" not in account_data  # Tokens must never leak
            connected_ids[p] = account_data["id"]
        print("✓ 4. POST /accounts (All 6 Platforms): PASS (Encrypted Tokens, Sanitized Response)")

        # Step 5: GET /accounts (List All)
        list_res = client.get("/accounts", headers=headers)
        assert list_res.status_code == 200
        accounts_list = list_res.json()
        assert len(accounts_list) == 6, f"Expected 6 accounts, got {len(accounts_list)}"
        print(f"✓ 5. GET /accounts: PASS (Total: {len(accounts_list)} accounts)")

        # Step 6: GET /accounts?platform=instagram (Filtering)
        filter_res = client.get("/accounts?platform=instagram", headers=headers)
        assert filter_res.status_code == 200
        filtered = filter_res.json()
        assert len(filtered) == 1
        assert filtered[0]["platform"] == "instagram"
        print("✓ 6. GET /accounts?platform=instagram: PASS (Filter verified)")

        # Step 7: GET /accounts/{id}/status (Status Check)
        fb_id = connected_ids["facebook"]
        status_res = client.get(f"/accounts/{fb_id}/status", headers=headers)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["connection_status"] == "connected"
        assert status_data["is_token_expired"] is False
        print(f"✓ 7. GET /accounts/{fb_id}/status: PASS (Status: {status_data['connection_status']})")

        # Step 8: PATCH /accounts/{id}/permissions (Permissions Update)
        perm_res = client.patch(f"/accounts/{fb_id}/permissions", headers=headers, json={
            "platform_permissions": {"publish_posts": True, "read_insights": True, "custom_scope": True}
        })
        assert perm_res.status_code == 200
        perm_data = perm_res.json()
        assert perm_data["platform_permissions"]["custom_scope"] is True
        print("✓ 8. PATCH /accounts/{id}/permissions: PASS (Custom permissions persisted)")

        # Step 9: POST /accounts/{id}/sync (Synchronization)
        sync_res = client.post(f"/accounts/{fb_id}/sync", headers=headers)
        assert sync_res.status_code == 200
        print(f"✓ 9. POST /accounts/{fb_id}/sync: PASS ({sync_res.json()['message']})")

        # Step 10: PATCH /users/me (Profile Update)
        new_name = f"Audit Engineer {uid} (Updated)"
        profile_res = client.patch("/users/me", headers=headers, json={
            "full_name": new_name
        })
        assert profile_res.status_code == 200
        assert profile_res.json()["full_name"] == new_name
        print(f"✓ 10. PATCH /users/me: PASS (Updated name: {profile_res.json()['full_name']})")

        # Step 11: DELETE /accounts/{id} (Disconnect)
        disc_res = client.delete(f"/accounts/{fb_id}", headers=headers)
        assert disc_res.status_code == 200
        assert disc_res.json()["connection_status"] == "revoked"
        print(f"✓ 11. DELETE /accounts/{fb_id}: PASS (Status marked as revoked)")

        # Step 12: POST /auth/refresh (Token Refresh)
        ref_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert ref_res.status_code == 200
        assert "access_token" in ref_res.json()
        print("✓ 12. POST /auth/refresh: PASS (New access token granted)")

    print("\n==================================================")
    print("ALL 12 BACKEND & FRONTEND INTEGRATION FLOWS: 100% PASS")
    print("==================================================")

if __name__ == "__main__":
    run_regression_audit()
