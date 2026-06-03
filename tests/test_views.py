from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import create_server
from billing.yookassa_client import YooKassaClient
from auth.models import User, UserRole
from core.models import TutorStatus
from infra.tutor_filter import TutorFilterPg
from infra.users import UsersPg
from infra.views import TutorProfileViewsPg
from services.views import TutorProfileViewService
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
async def test_views_pg_upsert_updates_viewed_at(db_connection):
    viewer = User(
        id=uuid4(),
        first_name="Viewer",
        last_name="User",
        email=f"viewer-{uuid4()}@example.com",
        role=UserRole.USER,
    )
    users = UsersPg(db_connection)
    await users.create(viewer, "hash")
    tutor = await seed_tutor(db_connection, status=TutorStatus.APPROVED)

    views = TutorProfileViewsPg(db_connection)
    await views.upsert_view(viewer.id, tutor.id)
    first = await views.list_recent(viewer.id, limit=3)
    assert len(first) == 1
    assert first[0].tutor_id == tutor.id

    await views.upsert_view(viewer.id, tutor.id)
    second = await views.list_recent(viewer.id, limit=3)
    assert second[0].viewed_at >= first[0].viewed_at


@pytest.mark.asyncio
async def test_list_recent_profiles_returns_last_three(db_connection):
    viewer = User(
        id=uuid4(),
        first_name="Viewer",
        last_name="User",
        email=f"viewer-{uuid4()}@example.com",
        role=UserRole.USER,
    )
    users = UsersPg(db_connection)
    await users.create(viewer, "hash")

    tutors = []
    for _ in range(4):
        tutor = await seed_tutor(db_connection, status=TutorStatus.APPROVED)
        tutors.append(tutor)

    service = TutorProfileViewService(
        views=TutorProfileViewsPg(db_connection),
        tutor_filter=TutorFilterPg(db_connection),
        users=users,
    )
    for tutor in tutors:
        await service.record_view(viewer.id, tutor.id)

    recent = await service.list_recent_profiles(viewer.id, limit=3)
    assert len(recent) == 3
    assert recent[0].id == tutors[3].id
    assert recent[1].id == tutors[2].id
    assert recent[2].id == tutors[1].id


@pytest.mark.asyncio
async def test_api_recent_tutor_profiles_endpoint(api_app, db_connection):
    email = f"viewer-{uuid4()}@example.com"
    tutors = []
    for _ in range(3):
        tutors.append(await seed_tutor(db_connection, status=TutorStatus.APPROVED))
    await db_connection.commit()

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register = await client.post(
            "/auth/register",
            json={
                "first_name": "Anna",
                "last_name": "User",
                "email": email,
                "password": "secret-password",
            },
        )
        assert register.status_code == 200
        login = await client.post(
            "/auth/login",
            json={"email": email, "password": "secret-password"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for tutor in tutors:
            viewed = await client.get(f"/tutors/{tutor.id}", headers=headers)
            assert viewed.status_code == 200

        recent = await client.get(
            "/users/me/recent-tutor-profiles",
            headers=headers,
        )
        assert recent.status_code == 200
        payload = recent.json()
        assert len(payload) == 3
        assert payload[0]["id"] == str(tutors[2].id)
        assert payload[1]["id"] == str(tutors[1].id)
        assert payload[2]["id"] == str(tutors[0].id)
