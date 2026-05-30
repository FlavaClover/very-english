from uuid import uuid4

import pytest

from core.exceptions import TutorNotFoundError
from core.models import Level, Tutor, TutorStatus, WorkFormat
from infra.tutors import TutorsPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_create_and_get_tutor(db_connection):
    tutors = TutorsPg(db_connection)
    tutor = Tutor(
        id=uuid4(),
        description="Math tutor",
        cities=["Moscow", "Kazan"],
        levels=[Level.A1, Level.B1],
        price=2000,
        lesson_duration=45,
        work_format=WorkFormat.HYBRID,
    )

    created = await tutors.create(tutor)
    fetched = await tutors.get(created.id)

    assert fetched.id == tutor.id
    assert fetched.description == tutor.description
    assert fetched.cities == tutor.cities
    assert fetched.levels == tutor.levels
    assert fetched.price == tutor.price
    assert fetched.lesson_duration == tutor.lesson_duration
    assert fetched.work_format == tutor.work_format


@pytest.mark.asyncio
async def test_get_tutor_not_found_raises(db_connection):
    tutors = TutorsPg(db_connection)

    with pytest.raises(TutorNotFoundError):
        await tutors.get(uuid4())


@pytest.mark.asyncio
async def test_update_tutor(db_connection):
    tutors = TutorsPg(db_connection)
    tutor = await seed_tutor(db_connection)
    updated = Tutor(
        id=tutor.id,
        description="Updated description",
        cities=["Saint Petersburg"],
        levels=[Level.C1],
        price=3000,
        lesson_duration=90,
        work_format=WorkFormat.OFFLINE,
    )

    result = await tutors.update(tutor.id, updated)
    fetched = await tutors.get(tutor.id)

    assert result == fetched
    assert fetched.description == "Updated description"
    assert fetched.cities == ["Saint Petersburg"]
    assert fetched.levels == [Level.C1]
    assert fetched.price == 3000
    assert fetched.lesson_duration == 90
    assert fetched.work_format == WorkFormat.OFFLINE


@pytest.mark.asyncio
async def test_update_tutor_not_found_raises(db_connection):
    tutors = TutorsPg(db_connection)
    tutor = Tutor(
        id=uuid4(),
        description="Missing",
        cities=["Moscow"],
        levels=[Level.A1],
        price=1000,
        lesson_duration=60,
        work_format=WorkFormat.ONLINE,
    )

    with pytest.raises(TutorNotFoundError):
        await tutors.update(uuid4(), tutor)


@pytest.mark.asyncio
async def test_set_status_appends_history(db_connection):
    tutors = TutorsPg(db_connection)
    tutor = await seed_tutor(db_connection, status=TutorStatus.DRAFT)

    await tutors.set_status(tutor.id, TutorStatus.MODERATION)
    await tutors.set_status(tutor.id, TutorStatus.APPROVED)

    history = await tutors.statuses(tutor.id)

    assert len(history) == 3
    assert history[0].status == TutorStatus.DRAFT
    assert history[1].status == TutorStatus.MODERATION
    assert history[2].status == TutorStatus.APPROVED
    assert history[0].created_at <= history[1].created_at <= history[2].created_at


@pytest.mark.asyncio
async def test_status_history_ordered_by_seq(db_connection):
    from sqlalchemy import text

    tutors = TutorsPg(db_connection)
    tutor = await seed_tutor(db_connection, status=TutorStatus.DRAFT)
    await tutors.set_status(tutor.id, TutorStatus.MODERATION)
    await tutors.set_status(tutor.id, TutorStatus.APPROVED)

    seq_rows = await db_connection.execute(
        text(
            """
            SELECT seq, status
            FROM status_history
            WHERE tutor_id = :tutor_id
            ORDER BY seq ASC
            """
        ),
        dict(tutor_id=tutor.id),
    )
    expected_statuses = [
        TutorStatus(row["status"]) for row in seq_rows.mappings().all()
    ]

    history = await tutors.statuses(tutor.id)

    assert [item.status for item in history] == expected_statuses
    assert expected_statuses == [
        TutorStatus.DRAFT,
        TutorStatus.MODERATION,
        TutorStatus.APPROVED,
    ]
