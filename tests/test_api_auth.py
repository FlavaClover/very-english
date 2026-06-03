from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import create_server


@pytest.fixture
def api_app(async_engine):
    database_url = str(async_engine.url)
    app = create_server(
        database_url=database_url,
        jwt_secret_key="test-jwt-secret-key-for-pytest!!",
        cors_allow_origins=["*"],
        s3_bucket="test-bucket",
        aws_endpoint_url="http://localhost:9000",
        yookassa_shop_id="test-shop",
        yookassa_secret_key="test-secret",
    )
    app.state.db_engine = async_engine
    return app


@pytest.mark.asyncio
async def test_register_and_login(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"user-{uuid4()}@example.com"
        register_response = await client.post(
            "/auth/register",
            json={
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": email,
                "password": "secret-password",
            },
        )
        assert register_response.status_code == 200
        assert register_response.json()["email"] == email

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": "secret-password"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        me_response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email


@pytest.mark.asyncio
async def test_register_tutor_minimal(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tutor-{uuid4()}@example.com"
        register_response = await client.post(
            "/auth/register/tutor",
            json={
                "first_name": "Anna",
                "last_name": "Petrova",
                "email": email,
                "password": "secret-password",
            },
        )
        assert register_response.status_code == 200
        body = register_response.json()
        assert body["email"] == email
        assert body["role"] == "tutor"

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": "secret-password"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
