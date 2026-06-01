from uuid import uuid4

import pytest

from auth.exceptions import UserNotFoundError
from auth.models import User, UserRole
from infra.users import UsersPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_create_and_get_user(db_connection):
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        role=UserRole.USER,
    )

    created = await users.create(user, "hashed-password")
    fetched = await users.get(created.id)

    assert fetched.id == user.id
    assert fetched.first_name == "Ivan"
    assert fetched.last_name == "Petrov"
    assert fetched.email == "ivan@example.com"
    assert fetched.role is UserRole.USER
    assert fetched.photo is None


@pytest.mark.asyncio
async def test_get_user_not_found_raises(db_connection):
    users = UsersPg(db_connection)

    with pytest.raises(UserNotFoundError):
        await users.get(uuid4())


@pytest.mark.asyncio
async def test_get_by_email_and_password_hash(db_connection):
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Anna",
        last_name="Smirnova",
        email="anna@example.com",
        role=UserRole.ADMIN,
    )
    await users.create(user, "secret-hash")

    fetched = await users.get_by_email("anna@example.com")
    password_hash = await users.get_password_hash(fetched.id)

    assert fetched.email == "anna@example.com"
    assert password_hash == "secret-hash"


@pytest.mark.asyncio
async def test_is_email_taken(db_connection):
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Olga",
        last_name="Ivanova",
        email="olga@example.com",
        role=UserRole.USER,
    )
    await users.create(user, "hash")

    assert await users.is_email_taken("olga@example.com") is True
    assert await users.is_email_taken("other@example.com") is False


@pytest.mark.asyncio
async def test_set_photo(db_connection):
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Maria",
        last_name="Kuznetsova",
        email="maria@example.com",
        role=UserRole.USER,
    )
    created = await users.create(user, "hash")

    updated = await users.set_photo(created.id, "avatar.png")
    assert updated.photo == "avatar.png"

    cleared = await users.set_photo(created.id, None)
    assert cleared.photo is None


@pytest.mark.asyncio
async def test_link_tutor(db_connection):
    tutor = await seed_tutor(db_connection)
    users = UsersPg(db_connection)
    user = User(
        id=uuid4(),
        first_name="Tutor",
        last_name="User",
        email="tutor@example.com",
        role=UserRole.TUTOR,
    )
    created = await users.create(user, "hash")
    await users.link_tutor(created.id, tutor.id)

    tutor_id = await users.get_tutor_id(created.id)
    assert tutor_id == tutor.id

    linked = await users.get_by_tutor_id(tutor.id)
    assert linked is not None
    assert linked.id == created.id
