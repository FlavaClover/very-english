import pytest
from sqlalchemy import text

from core.models import Advantage, Point
from infra.advantages import AdvantagesPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_add_get_and_remove_advantage(db_connection):
    tutor = await seed_tutor(db_connection)
    advantages = AdvantagesPg(db_connection)
    advantage = Advantage(
        video="intro.mp4",
        points=[Point(text="Fast progress"), Point(text="Native speaker")],
    )

    added = await advantages.add(tutor.id, advantage)
    assert added == advantage
    assert await advantages.is_exists(tutor.id) is True

    fetched = await advantages.get(tutor.id)
    assert fetched == advantage

    await advantages.remove(tutor.id)
    assert await advantages.is_exists(tutor.id) is False
    assert await advantages.get(tutor.id) is None


@pytest.mark.asyncio
async def test_update_advantage_rewrites_video_and_points(db_connection):
    tutor = await seed_tutor(db_connection)
    advantages = AdvantagesPg(db_connection)
    await advantages.add(
        tutor.id,
        Advantage(video="old.mp4", points=[Point(text="Old point")]),
    )

    updated = Advantage(
        video="new.mp4",
        points=[Point(text="First"), Point(text="Second")],
    )
    result = await advantages.update(tutor.id, updated)

    assert result == updated
    assert await advantages.get(tutor.id) == updated


@pytest.mark.asyncio
async def test_points_ordered_by_seq(db_connection):
    tutor = await seed_tutor(db_connection)
    advantages = AdvantagesPg(db_connection)
    await advantages.add(
        tutor.id,
        Advantage(
            video="intro.mp4",
            points=[
                Point(text="first"),
                Point(text="second"),
                Point(text="third"),
            ],
        ),
    )

    seq_rows = await db_connection.execute(
        text(
            """
            SELECT seq, text
            FROM points
            WHERE tutor_id = :tutor_id
            ORDER BY seq ASC
            """
        ),
        dict(tutor_id=tutor.id),
    )
    expected_texts = [row["text"] for row in seq_rows.mappings().all()]

    fetched = await advantages.get(tutor.id)
    assert fetched is not None
    assert [point.text for point in fetched.points] == expected_texts
    assert expected_texts == ["first", "second", "third"]
