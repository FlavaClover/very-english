import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock

from api.server import create_server
from billing.yookassa_client import YooKassaClient


@pytest.fixture
def webhook_api_app(async_engine):
    database_url = str(async_engine.url)
    app = create_server(
        database_url=database_url,
        jwt_secret_key="test-jwt-secret-key-for-pytest!!",
        cors_allow_origins=["*"],
        s3_bucket="test-bucket",
        aws_endpoint_url="http://localhost:9000",
        yookassa_shop_id="test-shop",
        yookassa_secret_key="test-secret",
        yookassa_webhook_ip_check_enabled=True,
    )
    app.state.db_engine = async_engine
    app.state.yookassa_client = MagicMock(spec=YooKassaClient)
    return app


@pytest.mark.asyncio
async def test_yookassa_webhook_rejects_forbidden_ip(webhook_api_app):
    transport = ASGITransport(app=webhook_api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/billing/webhooks/yookassa",
            json={"event": "payment.succeeded", "object": {}},
            headers={"X-Forwarded-For": "8.8.8.8"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_yookassa_webhook_accepts_official_ip(webhook_api_app):
    transport = ASGITransport(app=webhook_api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/billing/webhooks/yookassa",
            json={"event": "payment.succeeded", "object": {}},
            headers={"X-Forwarded-For": "77.75.156.11"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
