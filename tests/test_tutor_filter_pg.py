import pytest

from core.exceptions import TutorNotFoundError
from core.models import Contact, Level, Tag, TutorStatus, WorkFormat
from infra.tutor_filter import TutorFilterPg
from tests.conftest import seed_tutor


@pytest.mark.asyncio
async def test_get_profile(db_connection):
    tutor = await seed_tutor(
        db_connection,
        description="Profile tutor",
        cities=["Moscow"],
        levels=[Level.B1],
        price=2500,
        lesson_duration=50,
        work_format=WorkFormat.HYBRID,
        tag_names=["grammar", "speaking"],
        status=TutorStatus.APPROVED,
        contacts=[Contact(name="telegram", value="@profile")],
    )
    tutor_filter = TutorFilterPg(db_connection)

    profile = await tutor_filter.get(tutor.id)

    assert profile.id == tutor.id
    assert profile.description == "Profile tutor"
    assert profile.cities == ["Moscow"]
    assert profile.levels == [Level.B1]
    assert profile.price == 2500
    assert profile.lesson_duration == 50
    assert profile.work_format == WorkFormat.HYBRID
    assert profile.status == TutorStatus.APPROVED
    assert profile.contacts == [Contact(name="telegram", value="@profile")]
    assert Tag(name="grammar") in profile.tags
    assert Tag(name="speaking") in profile.tags
    assert profile.advantage.video == ""
    assert profile.advantage.points == []


@pytest.mark.asyncio
async def test_get_profile_not_found_raises(db_connection):
    from uuid import uuid4

    tutor_filter = TutorFilterPg(db_connection)

    with pytest.raises(TutorNotFoundError):
        await tutor_filter.get(uuid4())


@pytest.mark.asyncio
async def test_filter_returns_only_approved(db_connection):
    await seed_tutor(
        db_connection,
        description="Approved tutor",
        price=1000,
        status=TutorStatus.APPROVED,
        tag_names=["grammar"],
    )
    await seed_tutor(
        db_connection,
        description="Draft tutor",
        price=1000,
        status=TutorStatus.DRAFT,
        tag_names=["grammar"],
    )
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.filter(page=1, page_size=10)

    assert len(profiles) == 1
    assert profiles[0].description == "Approved tutor"
    assert profiles[0].status == TutorStatus.APPROVED


@pytest.mark.asyncio
async def test_filter_by_price_levels_cities_and_tags(db_connection):
    await seed_tutor(
        db_connection,
        description="Match",
        cities=["Moscow"],
        levels=[Level.A1, Level.B2],
        price=1500,
        work_format=WorkFormat.ONLINE,
        tag_names=["grammar", "speaking"],
        status=TutorStatus.APPROVED,
    )
    await seed_tutor(
        db_connection,
        description="Too expensive",
        cities=["Moscow"],
        levels=[Level.A1],
        price=5000,
        work_format=WorkFormat.ONLINE,
        tag_names=["grammar"],
        status=TutorStatus.APPROVED,
    )
    await seed_tutor(
        db_connection,
        description="Wrong city",
        cities=["Kazan"],
        levels=[Level.A1],
        price=1500,
        work_format=WorkFormat.ONLINE,
        tag_names=["grammar"],
        status=TutorStatus.APPROVED,
    )
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.filter(
        price_from=1000,
        price_to=2000,
        levels=[Level.A1],
        work_formats=[WorkFormat.ONLINE],
        cities=["Moscow"],
        tags=[Tag(name="grammar"), Tag(name="speaking")],
        page=1,
        page_size=10,
    )

    assert len(profiles) == 1
    assert profiles[0].description == "Match"


@pytest.mark.asyncio
async def test_for_moderation_returns_profiles_with_moderation_status(db_connection):
    await seed_tutor(
        db_connection,
        description="On moderation",
        status=TutorStatus.MODERATION,
    )
    await seed_tutor(
        db_connection,
        description="Already approved",
        status=TutorStatus.APPROVED,
    )
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.for_moderation()

    assert len(profiles) == 1
    assert profiles[0].description == "On moderation"
    assert profiles[0].status == TutorStatus.MODERATION
