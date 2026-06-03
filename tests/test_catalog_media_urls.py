from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import create_server
from auth.models import User, UserRole
from core.models import TutorStatus
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
    return app


@pytest.mark.asyncio
async def test_catalog_tutor_media_urls_public(api_app, db_connection):
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
    await db_connection.commit()

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        photo = await client.get(f"/tutors/{tutor.id}/photo/url")
        assert photo.status_code == 200
        assert photo.json()["url"] == f"https://in-memory.test/{user.photo}"

        video = await client.get(f"/tutors/{tutor.id}/visit-video/url")
        assert video.status_code == 404

        achievements = await client.get(f"/tutors/{tutor.id}/achievements/urls")
        assert achievements.status_code == 200
        assert achievements.json() == []
