import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import get_password_hash


@pytest.fixture
def client():
    return TestClient(app)


def test_google_auth_new_user_creation(client: TestClient):
    """Test registering a new user via Google Sign-In."""
    uid = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/v1/auth/google",
        json={"credential": f"mock_google_{uid}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == f"{uid}@socialpilot.test"
    assert data["user"]["auth_provider"] == "google"


def test_google_auth_account_linking_existing_user(client: TestClient):
    """Test linking Google authentication to an existing email/password account."""
    uid = uuid.uuid4().hex[:8]
    email = f"existing_{uid}@socialpilot.test"

    # Pre-create email user via register endpoint
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Existing User"
    })
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # Perform Google Sign-In with credential returning same email
    g_res = client.post(
        "/api/v1/auth/google",
        json={"credential": f"mock_google_existing_{uid}"}
    )
    assert g_res.status_code == 200
    data = g_res.json()
    assert data["user"]["id"] == user_id
    assert data["user"]["email"] == email


def test_google_auth_existing_google_user_login(client: TestClient):
    """Test logging into an already existing Google-linked user."""
    uid = uuid.uuid4().hex[:8]
    credential = f"mock_google_repeat_{uid}"

    # First sign in (creates account)
    res1 = client.post("/api/v1/auth/google", json={"credential": credential})
    assert res1.status_code == 200
    user_id_1 = res1.json()["user"]["id"]

    # Second sign in (should log into same account)
    res2 = client.post("/api/v1/auth/google", json={"credential": credential})
    assert res2.status_code == 200
    user_id_2 = res2.json()["user"]["id"]
    assert user_id_1 == user_id_2


def test_google_auth_invalid_credential(client: TestClient):
    """Test rejection of empty credential."""
    response = client.post("/api/v1/auth/google", json={"credential": ""})
    assert response.status_code == 400
