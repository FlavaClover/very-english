from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import create_server
from billing.yookassa_client import YooKassaClient
from auth.models import User, UserRole
from core.models import TutorStatus
from billing.subscriptions import (
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from infra.subscriptions import SubscriptionsPg
from infra.users import UsersPg
from tests.conftest import seed_tutor
from tests.test_auth import InMemoryMedia


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
    app.state.media = InMemoryMedia()
    app.state.yookassa_client = MagicMock(spec=YooKassaClient)
    return app


@pytest.mark.asyncio
async def test_catalog_tutor_profile_includes_media_urls(api_app, db_connection):
    tutor = await seed_tutor(db_connection, status=TutorStatus.APPROVED)
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Anna",
        last_name="Tutor",
        email=f"tutor-{uuid4()}@example.com",
        role=UserRole.TUTOR,
        photo="users/avatar.png",
    )
    created = await users.create(user, "hash")
    await users.link_tutor(created.id, tutor.id)
    now = datetime.now(UTC)
    subscriptions = SubscriptionsPg(db_connection)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=created.id,
            plan_id=SubscriptionPlanId.PRO,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        ),
    )
    await db_connection.commit()

    viewer_email = f"viewer-{uuid4()}@example.com"
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register = await client.post(
            "/auth/register",
            json={
                "first_name": "Viewer",
                "last_name": "User",
                "email": viewer_email,
                "password": "secret-password",
            },
        )
        assert register.status_code == 200
        login = await client.post(
            "/auth/login",
            json={"email": viewer_email, "password": "secret-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = await client.get(f"/tutors/{tutor.id}", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["photo_url"] == f"https://in-memory.test/{user.photo}"
        assert payload["subscription_plan"] == "pro"
        assert payload["advantage"]["video_url"] is None
        assert payload["achievements"] == []
