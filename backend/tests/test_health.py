import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.fixture
def mock_redis():
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    with patch("app.api.v1.health.get_redis_client", return_value=mock_client):
        yield mock_client


@pytest.mark.asyncio
async def test_health_endpoint(mock_redis):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["databases"]["postgresql"] == "connected"
        assert data["databases"]["mongodb"] == "connected"
        assert data["databases"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_v1_health_endpoint(mock_redis):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["databases"]["postgresql"] == "connected"
        assert data["databases"]["mongodb"] == "connected"
        assert data["databases"]["redis"] == "connected"
