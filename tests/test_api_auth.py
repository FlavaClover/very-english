from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import create_server
from tests.email_verification_helpers import FixedCodeGenerator, InMemoryEmailQueue
from tests.test_auth import FakeVkIdOAuth


@pytest.fixture
def api_app(async_engine, redis_url):
    database_url = str(async_engine.url)
    app = create_server(
        database_url=database_url,
        jwt_secret_key="test-jwt-secret-key-for-pytest!!",
        cors_allow_origins=["*"],
        s3_bucket="test-bucket",
        aws_endpoint_url="http://localhost:9000",
        yookassa_shop_id="test-shop",
        yookassa_secret_key="test-secret",
        redis_url=redis_url,
        email_code_pepper="test-email-pepper",
    )
    app.state.db_engine = async_engine
    app.state.vkid_client = FakeVkIdOAuth()
    app.state.test_email_queue = InMemoryEmailQueue()
    app.state.email_code_generator = FixedCodeGenerator("123456")
    return app


async def _register_with_verified_email(client, email: str) -> dict:
    send_response = await client.post("/auth/send-code", json={"email": email})
    assert send_response.status_code == 204

    verify_response = await client.post(
        "/auth/verify-email",
        json={"email": email, "code": "123456"},
    )
    assert verify_response.status_code == 200
    verification_id = verify_response.json()["email_verification_id"]

    register_response = await client.post(
        "/auth/register",
        json={
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": email,
            "password": "secret-password",
            "email_verification_id": verification_id,
        },
    )
    assert register_response.status_code == 200
    return register_response.json()


@pytest.mark.asyncio
async def test_register_and_login(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"user-{uuid4()}@example.com"
        body = await _register_with_verified_email(client, email)
        assert body["email"] == email

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
async def test_login_vkid_endpoint(api_app):
    api_app.state.vkid_client = FakeVkIdOAuth(
        user_id=987654321,
        email="vk-user@example.com",
    )

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/auth/login/vkid",
            json={
                "code": "vk-auth-code",
                "state": "e" * 32,
                "code_verifier": "f" * 43,
                "device_id": "device-42",
            },
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
        assert me_response.json()["email"] == "vk-user@example.com"


@pytest.mark.asyncio
async def test_register_tutor_minimal(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tutor-{uuid4()}@example.com"
        await client.post("/auth/send-code", json={"email": email})
        verify_response = await client.post(
            "/auth/verify-email",
            json={"email": email, "code": "123456"},
        )
        verification_id = verify_response.json()["email_verification_id"]

        register_response = await client.post(
            "/auth/register/tutor",
            json={
                "first_name": "Anna",
                "last_name": "Petrova",
                "email": email,
                "password": "secret-password",
                "email_verification_id": verification_id,
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
