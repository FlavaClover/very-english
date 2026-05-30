import pytest

from core.models import Achievement
from infra.achievements import AchievementsPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_add_get_and_remove_achievement(db_connection):
    tutor = await seed_tutor(db_connection)
    achievements = AchievementsPg(db_connection)

    added = await achievements.add(tutor.id, Achievement(image="cert.png"))
    assert added == Achievement(image="cert.png")

    result = await achievements.get(tutor.id)
    assert result == [Achievement(image="cert.png")]

    await achievements.remove(tutor.id, "cert.png")
    assert await achievements.get(tutor.id) == []


@pytest.mark.asyncio
async def test_get_achievements_ordered_by_created_at(db_connection):
    tutor = await seed_tutor(db_connection)
    achievements = AchievementsPg(db_connection)

    await achievements.add(tutor.id, Achievement(image="first.png"))
    await achievements.add(tutor.id, Achievement(image="second.png"))

    result = await achievements.get(tutor.id)

    assert [item.image for item in result] == ["first.png", "second.png"]
