from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from auth.models import User, UserRole
from core.models import Contact, Level, Tutor, TutorStatus, WorkFormat
from infra.contacts import ContactsPg
from infra.tags import TagsPg
from infra.tutors import TutorsPg
from infra.users import UsersPg


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine", driver=None) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(postgres_container) -> str:
    url = postgres_container.get_connection_url()
    if url.startswith("postgresql://") and "psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@pytest.fixture(scope="session")
def _run_migrations(database_url) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def engine(database_url, _run_migrations) -> Engine:
    sync_engine = create_engine(database_url)
    return sync_engine


@pytest.fixture(scope="session")
def _async_engine_raw(database_url, _run_migrations) -> AsyncEngine:
    async_engine = create_async_engine(database_url, poolclass=NullPool)
    return async_engine


@pytest.fixture(scope="function")
def clean_db(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                TRUNCATE TABLE
                    tutor_profile_view_events,
                    tutor_profile_views,
                    tutor_subscription_history,
                    tutor_subscriptions,
                    payments,
                    subscription_plans,
                    users_tutor,
                    users,
                    points,
                    videos,
                    status_history,
                    profile_tags,
                    achievements,
                    contacts,
                    tags,
                    tutors
                RESTART IDENTITY CASCADE
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO subscription_plans (id, price_rub, billing_interval)
                VALUES
                    ('base', 990, 'month'),
                    ('pro', 1990, 'month')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        conn.commit()


@pytest.fixture(scope="function")
def async_engine(clean_db, _async_engine_raw: AsyncEngine) -> AsyncEngine:
    return _async_engine_raw


@pytest.fixture(scope="function")
async def db_connection(async_engine: AsyncEngine):
    async with async_engine.connect() as conn:
        yield conn


async def seed_tutor(
    db_connection,
    description: str = "Experienced tutor",
    cities: list[str] | None = None,
    levels: list[Level] | None = None,
    price: int = 1500,
    lesson_duration: int = 60,
    work_format: WorkFormat = WorkFormat.ONLINE,
    tag_names: list[str] | None = None,
    status: TutorStatus = TutorStatus.DRAFT,
    contacts: list[Contact] | None = None,
    tutor_id: UUID | None = None,
) -> Tutor:
    """Создаёт тутора с тегами, контактами и начальным статусом."""
    cities = cities or ["Moscow"]
    levels = levels or [Level.A1, Level.B2]
    tag_names = tag_names or ["grammar"]
    contacts = contacts or [Contact(name="telegram", value="@tutor")]

    tags = TagsPg(db_connection)
    for tag_name in tag_names:
        if not await tags.is_exists(tag_name):
            await tags.add(tag_name)

    tutor = Tutor(
        id=tutor_id or uuid4(),
        description=description,
        cities=cities,
        levels=levels,
        price=price,
        lesson_duration=lesson_duration,
        work_format=work_format,
    )
    tutors = TutorsPg(db_connection)
    created = await tutors.create(tutor)
    await tutors.set_status(created.id, status)

    contacts_pg = ContactsPg(db_connection)
    for contact in contacts:
        await contacts_pg.add(created.id, contact)

    for tag_name in tag_names:
        await tags.link_tag_to_tutor(created.id, tag_name)

    return await tutors.get(created.id)


async def seed_tutor_user(
    db_connection,
    autopayment_consent: bool = False,
) -> User:
    """Создаёт пользователя с ролью tutor для тестов подписок."""
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Tutor",
        last_name="User",
        email=f"tutor-{uuid4()}@example.com",
        role=UserRole.TUTOR,
        autopayment_consent=autopayment_consent,
    )
    return await users.create(user, "hash")
