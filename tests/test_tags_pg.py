import pytest

from core.exceptions import TagNotFoundError
from core.models import Tag
from infra.tags import TagsPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_add_get_and_remove_tag(db_connection):
    tags = TagsPg(db_connection)

    await tags.add("grammar")
    assert await tags.is_exists("grammar") is True
    assert await tags.get("grammar") == Tag(name="grammar")

    all_tags = await tags.get_all()
    assert all_tags == [Tag(name="grammar")]

    await tags.remove("grammar")
    assert await tags.is_exists("grammar") is False


@pytest.mark.asyncio
async def test_remove_missing_tag_raises(db_connection):
    tags = TagsPg(db_connection)

    with pytest.raises(TagNotFoundError):
        await tags.remove("missing")


@pytest.mark.asyncio
async def test_get_missing_tag_raises(db_connection):
    tags = TagsPg(db_connection)

    with pytest.raises(TagNotFoundError):
        await tags.get("missing")


@pytest.mark.asyncio
async def test_link_and_unlink_tag_to_tutor(db_connection):
    tutor = await seed_tutor(db_connection, tag_names=["grammar"])
    tags = TagsPg(db_connection)
    await tags.add("speaking")

    await tags.link_tag_to_tutor(tutor.id, "speaking")
    linked = await tags.get_tags_by_tutor(tutor.id)

    assert Tag(name="grammar") in linked
    assert Tag(name="speaking") in linked

    await tags.unlink_tag_from_tutor(tutor.id, "grammar")
    linked = await tags.get_tags_by_tutor(tutor.id)

    assert linked == [Tag(name="speaking")]


@pytest.mark.asyncio
async def test_link_missing_tag_raises(db_connection):
    tutor = await seed_tutor(db_connection, tag_names=[])
    tags = TagsPg(db_connection)

    with pytest.raises(TagNotFoundError):
        await tags.link_tag_to_tutor(tutor.id, "missing")


@pytest.mark.asyncio
async def test_unlink_missing_tag_raises(db_connection):
    tutor = await seed_tutor(db_connection, tag_names=["grammar"])
    tags = TagsPg(db_connection)

    with pytest.raises(TagNotFoundError):
        await tags.unlink_tag_from_tutor(tutor.id, "missing")
