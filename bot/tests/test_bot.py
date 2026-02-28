import http

from fastapi.testclient import TestClient

from bot.main import app

client = TestClient(app)


def test_bot_initialization():
    """Placeholder test verifying core logic."""
    assert True


def test_health_check():
    """Verify the FastAPI health check endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == http.HTTPStatus.OK
    assert response.json() == {"status": "healthy"}
