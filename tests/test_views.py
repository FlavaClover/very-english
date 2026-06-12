from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.server import create_server
from billing.yookassa_client import YooKassaClient
from auth.models import User, UserRole
from core.models import TutorStatus
from infra.tutor_filter import TutorFilterPg
from infra.users import UsersPg
from infra.views import TutorProfileViewAnalyticsPg, TutorProfileViewsPg
from services.views import TutorProfileViewService
from tests.conftest import seed_tutor
from tests.email_verification_helpers import (
    FixedCodeGenerator,
    InMemoryEmailQueue,
    register_user_via_api,
)
from tests.test_auth import FakeVkIdOAuth, InMemoryMedia


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
    app.state.media = InMemoryMedia()
    app.state.vkid_client = FakeVkIdOAuth()
    app.state.yookassa_client = MagicMock(spec=YooKassaClient)
    app.state.test_email_queue = InMemoryEmailQueue()
    app.state.email_code_generator = FixedCodeGenerator("123456")
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
        view_analytics=TutorProfileViewAnalyticsPg(db_connection),
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
        await register_user_via_api(
            client,
            email,
            first_name="Anna",
            last_name="User",
        )
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


async def _count_view_events(db_connection, user_id) -> int:
    result = await db_connection.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM tutor_profile_view_events
            WHERE user_id = :user_id
            """
        ),
        dict(user_id=user_id),
    )
    return result.mappings().one()["count"]


@pytest.mark.asyncio
async def test_record_view_writes_analytics_event_per_view(db_connection):
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

    service = TutorProfileViewService(
        views=TutorProfileViewsPg(db_connection),
        view_analytics=TutorProfileViewAnalyticsPg(db_connection),
        tutor_filter=TutorFilterPg(db_connection),
        users=users,
    )
    await service.record_view(viewer.id, tutor.id)
    await service.record_view(viewer.id, tutor.id)

    recent = await service.list_recent_profiles(viewer.id, limit=3)
    assert len(recent) == 1
    assert await _count_view_events(db_connection, viewer.id) == 2


@pytest.mark.asyncio
async def test_remove_recent_view_keeps_analytics_events(db_connection):
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

    service = TutorProfileViewService(
        views=TutorProfileViewsPg(db_connection),
        view_analytics=TutorProfileViewAnalyticsPg(db_connection),
        tutor_filter=TutorFilterPg(db_connection),
        users=users,
    )
    await service.record_view(viewer.id, tutor.id)
    await service.remove_recent_view(viewer.id, tutor.id)

    recent = await service.list_recent_profiles(viewer.id, limit=3)
    assert recent == []
    assert await _count_view_events(db_connection, viewer.id) == 1


@pytest.mark.asyncio
async def test_clear_recent_views_keeps_analytics_events(db_connection):
    viewer = User(
        id=uuid4(),
        first_name="Viewer",
        last_name="User",
        email=f"viewer-{uuid4()}@example.com",
        role=UserRole.USER,
    )
    users = UsersPg(db_connection)
    await users.create(viewer, "hash")
    tutors = [
        await seed_tutor(db_connection, status=TutorStatus.APPROVED) for _ in range(2)
    ]

    service = TutorProfileViewService(
        views=TutorProfileViewsPg(db_connection),
        view_analytics=TutorProfileViewAnalyticsPg(db_connection),
        tutor_filter=TutorFilterPg(db_connection),
        users=users,
    )
    for tutor in tutors:
        await service.record_view(viewer.id, tutor.id)
    await service.clear_recent_views(viewer.id)

    recent = await service.list_recent_profiles(viewer.id, limit=3)
    assert recent == []
    assert await _count_view_events(db_connection, viewer.id) == 2


@pytest.mark.asyncio
async def test_api_clear_and_remove_recent_tutor_profiles(api_app, db_connection):
    email = f"viewer-{uuid4()}@example.com"
    tutors = [
        await seed_tutor(db_connection, status=TutorStatus.APPROVED) for _ in range(3)
    ]
    await db_connection.commit()

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register_user_via_api(
            client,
            email,
            first_name="Anna",
            last_name="User",
        )
        login = await client.post(
            "/auth/login",
            json={"email": email, "password": "secret-password"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for tutor in tutors:
            viewed = await client.get(f"/tutors/{tutor.id}", headers=headers)
            assert viewed.status_code == 200

        removed = await client.delete(
            f"/users/me/recent-tutor-profiles/{tutors[2].id}",
            headers=headers,
        )
        assert removed.status_code == 204

        recent = await client.get(
            "/users/me/recent-tutor-profiles",
            headers=headers,
        )
        assert recent.status_code == 200
        payload = recent.json()
        assert len(payload) == 2
        assert payload[0]["id"] == str(tutors[1].id)
        assert payload[1]["id"] == str(tutors[0].id)

        cleared = await client.delete(
            "/users/me/recent-tutor-profiles",
            headers=headers,
        )
        assert cleared.status_code == 204

        recent_after_clear = await client.get(
            "/users/me/recent-tutor-profiles",
            headers=headers,
        )
        assert recent_after_clear.status_code == 200
        assert recent_after_clear.json() == []
