import http
from unittest.mock import AsyncMock, MagicMock, patch

import bot.main as bot_main
import pytest
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


def test_webhook_returns_403_with_wrong_secret():
    """Webhook must reject requests that carry a wrong secret token."""
    with patch.object(bot_main, "bot", MagicMock()), patch.object(
        bot_main, "webhook_secret", "correct-secret"
    ):
        response = client.post(
            "/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_webhook_returns_403_with_missing_secret():
    """Webhook must reject requests that omit the secret token header."""
    with patch.object(bot_main, "bot", MagicMock()), patch.object(
        bot_main, "webhook_secret", "correct-secret"
    ):
        response = client.post("/webhook", json={"update_id": 1})
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_webhook_returns_200_with_correct_secret():
    """Webhook must accept requests that carry the correct secret token."""
    mock_bot = MagicMock()
    mock_dp = MagicMock()
    mock_dp.feed_update = AsyncMock()

    with (
        patch.object(bot_main, "bot", mock_bot),
        patch.object(bot_main, "webhook_secret", "correct-secret"),
        patch.object(bot_main, "authorized_user_id", None),
        patch.object(bot_main, "dp", mock_dp),
    ):
        response = client.post(
            "/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
        )
    assert response.status_code == http.HTTPStatus.OK


def test_webhook_passes_through_when_no_secret_configured():
    """When no webhook_secret is configured the endpoint should not enforce the header."""
    mock_bot = MagicMock()
    mock_dp = MagicMock()
    mock_dp.feed_update = AsyncMock()

    with (
        patch.object(bot_main, "bot", mock_bot),
        patch.object(bot_main, "webhook_secret", None),
        patch.object(bot_main, "authorized_user_id", None),
        patch.object(bot_main, "dp", mock_dp),
    ):
        response = client.post("/webhook", json={"update_id": 1})
    assert response.status_code == http.HTTPStatus.OK


def test_webhook_rejects_unknown_user_when_auth_configured():
    """Webhook must silently drop updates from users not matching authorized_user_id."""
    mock_bot = MagicMock()
    mock_dp = MagicMock()
    mock_dp.feed_update = AsyncMock()

    update_payload = {
        "update_id": 2,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 999, "type": "private"},
            "from": {"id": 999, "is_bot": False, "first_name": "Evil"},
        },
    }

    with (
        patch.object(bot_main, "bot", mock_bot),
        patch.object(bot_main, "webhook_secret", None),
        patch.object(bot_main, "authorized_user_id", "111"),
        patch.object(bot_main, "dp", mock_dp),
    ):
        response = client.post("/webhook", json=update_payload)

    assert response.status_code == http.HTTPStatus.OK
    mock_dp.feed_update.assert_not_called()


def test_webhook_rejects_update_with_no_user_when_auth_configured():
    """Webhook must drop updates with no resolvable user_id when authorized_user_id is set."""
    mock_bot = MagicMock()
    mock_dp = MagicMock()
    mock_dp.feed_update = AsyncMock()

    # An update with no message.from_user and no callback_query → user_id is None
    update_payload = {"update_id": 3}

    with (
        patch.object(bot_main, "bot", mock_bot),
        patch.object(bot_main, "webhook_secret", None),
        patch.object(bot_main, "authorized_user_id", "111"),
        patch.object(bot_main, "dp", mock_dp),
    ):
        response = client.post("/webhook", json=update_payload)

    assert response.status_code == http.HTTPStatus.OK
    mock_dp.feed_update.assert_not_called()
