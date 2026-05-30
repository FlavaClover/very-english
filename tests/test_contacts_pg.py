from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from core.exceptions import TutorNotFoundError
from core.models import Contact
from infra.contacts import ContactsPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_add_and_get_contacts(db_connection):
    tutor = await seed_tutor(
        db_connection,
        contacts=[Contact(name="telegram", value="@first")],
    )
    contacts = ContactsPg(db_connection)

    await contacts.add(tutor.id, Contact(name="email", value="tutor@example.com"))
    result = await contacts.get(tutor.id)

    assert len(result) == 2
    assert Contact(name="telegram", value="@first") in result
    assert Contact(name="email", value="tutor@example.com") in result


@pytest.mark.asyncio
async def test_add_contact_returns_updated_tutor(db_connection):
    tutor = await seed_tutor(
        db_connection,
        contacts=[Contact(name="telegram", value="@first")],
    )
    contacts = ContactsPg(db_connection)

    updated = await contacts.add(
        tutor.id,
        Contact(name="whatsapp", value="+79001234567"),
    )

    assert updated.id == tutor.id
    assert updated.description == tutor.description


@pytest.mark.asyncio
async def test_remove_contact(db_connection):
    tutor = await seed_tutor(
        db_connection,
        contacts=[
            Contact(name="telegram", value="@first"),
            Contact(name="email", value="tutor@example.com"),
        ],
    )
    contacts = ContactsPg(db_connection)

    await contacts.remove(tutor.id, "telegram")
    result = await contacts.get(tutor.id)

    assert result == [Contact(name="email", value="tutor@example.com")]


@pytest.mark.asyncio
async def test_remove_contact_not_found_raises(db_connection):
    tutor = await seed_tutor(db_connection)
    contacts = ContactsPg(db_connection)

    with pytest.raises(TutorNotFoundError):
        await contacts.remove(tutor.id, "missing")


@pytest.mark.asyncio
async def test_add_contact_to_missing_tutor_raises(db_connection):
    contacts = ContactsPg(db_connection)

    with pytest.raises(IntegrityError):
        await contacts.add(
            uuid4(),
            Contact(name="telegram", value="@ghost"),
        )
