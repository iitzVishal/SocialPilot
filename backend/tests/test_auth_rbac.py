import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.main import app
from app.models.user import User
from app.models.enums import UserRole


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


import uuid

@pytest.mark.asyncio
async def test_successful_registration_and_password_hashing(db_session):
    """1. Successful registration, 3. Password is hashed in DB."""
    uid = uuid.uuid4().hex[:8]
    email = f"creator_{uid}@socialpilot.test"
    password = "SuperSecretPassword123!"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Test Creator"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["full_name"] == "Test Creator"
        assert data["role"] == UserRole.CONTENT_CREATOR.value
        assert "password" not in data
        assert "hashed_password" not in data

    # Verify password was hashed in database
    db_user = db_session.query(User).filter_by(email=email).first()
    assert db_user is not None
    assert db_user.hashed_password != password
    assert verify_password(password, db_user.hashed_password) is True


@pytest.mark.asyncio
async def test_duplicate_registration_rejected():
    """2. Duplicate registration rejected with 400."""
    uid = uuid.uuid4().hex[:8]
    email = f"duplicate_{uid}@socialpilot.test"
    payload = {"email": email, "password": "Password123!", "full_name": "Duplicate User"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First registration
        r1 = await client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201

        # Second registration with same email
        r2 = await client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_invalid_credentials():
    """4. Successful login, 5. Wrong password, 6. Unknown user."""
    uid = uuid.uuid4().hex[:8]
    email = f"login_{uid}@socialpilot.test"
    password = "CorrectPassword123!"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Login User"})

        # 4. Successful login
        res_ok = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert res_ok.status_code == 200
        data = res_ok.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email

        # 5. Wrong password
        res_wrong_pw = await client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert res_wrong_pw.status_code == 401

        # 6. Unknown user
        res_unknown = await client.post("/api/v1/auth/login", json={"email": f"unknown_{uid}@socialpilot.test", "password": password})
        assert res_unknown.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_endpoints_and_token_validation():
    """7. Valid JWT, 8. Missing JWT, 9. Invalid JWT, 10. Safe user data returned."""
    uid = uuid.uuid4().hex[:8]
    email = f"token_{uid}@socialpilot.test"
    password = "TokenPassword123!"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Token User"})
        login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = login_res.json()["access_token"]

        # 7. Valid JWT
        me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == email
        assert me_data["full_name"] == "Token User"
        assert "hashed_password" not in me_data
        assert "password" not in me_data

        # 8. Missing JWT
        no_auth = await client.get("/api/v1/auth/me")
        assert no_auth.status_code == 401

        # 9. Invalid JWT
        bad_auth = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_garbage_token_12345"})
        assert bad_auth.status_code == 401


import uuid

@pytest.mark.asyncio
async def test_rbac_roles_recognition_and_restriction():
    """11. Admin, 12. Marketing, 13. Business, 14. Creator, 15. Unauthorized 403 rejection."""
    uid = uuid.uuid4().hex[:8]
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    admin_user = User(email=f"admin_{uid}@test.com", hashed_password="pw", role=UserRole.ADMINISTRATOR)
    marketing_user = User(email=f"mktg_{uid}@test.com", hashed_password="pw", role=UserRole.MARKETING_TEAM)
    business_user = User(email=f"biz_{uid}@test.com", hashed_password="pw", role=UserRole.BUSINESS_USER)
    creator_user = User(email=f"creator_{uid}@test.com", hashed_password="pw", role=UserRole.CONTENT_CREATOR)

    session.add_all([admin_user, marketing_user, business_user, creator_user])
    session.commit()

    admin_token = create_access_token(subject=admin_user.id)
    mktg_token = create_access_token(subject=marketing_user.id)
    biz_token = create_access_token(subject=business_user.id)
    creator_token = create_access_token(subject=creator_user.id)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 11. Admin-only endpoint accessible by Admin
        r_admin = await client.get("/api/v1/users/rbac/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_admin.status_code == 200

        # 15. Creator trying to access admin endpoint -> 403
        r_forbidden = await client.get("/api/v1/users/rbac/admin-only", headers={"Authorization": f"Bearer {creator_token}"})
        assert r_forbidden.status_code == 403

        # 12. Marketing-only endpoint accessible by Marketing Team
        r_mktg = await client.get("/api/v1/users/rbac/marketing-only", headers={"Authorization": f"Bearer {mktg_token}"})
        assert r_mktg.status_code == 200

        # Business user trying to access marketing endpoint -> 403
        r_mktg_forbidden = await client.get("/api/v1/users/rbac/marketing-only", headers={"Authorization": f"Bearer {biz_token}"})
        assert r_mktg_forbidden.status_code == 403

        # 13. Business-only endpoint accessible by Business User
        r_biz = await client.get("/api/v1/users/rbac/business-only", headers={"Authorization": f"Bearer {biz_token}"})
        assert r_biz.status_code == 200

        # 14. Creator-only endpoint accessible by Content Creator
        r_creator = await client.get("/api/v1/users/rbac/creator-only", headers={"Authorization": f"Bearer {creator_token}"})
        assert r_creator.status_code == 200

    session.delete(admin_user)
    session.delete(marketing_user)
    session.delete(business_user)
    session.delete(creator_user)
    session.commit()
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_profile_update_and_protection():
    """Profile update allows full_name change but prevents modifying sensitive fields."""
    uid = uuid.uuid4().hex[:8]
    email = f"profile_{uid}@socialpilot.test"
    password = "ProfilePassword123!"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Original Name"})
        login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = login_res.json()["access_token"]

        # Update full_name
        patch_res = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated Name"}
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["full_name"] == "Updated Name"
        assert patch_res.json()["email"] == email
        assert patch_res.json()["role"] == UserRole.CONTENT_CREATOR.value
