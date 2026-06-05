from datetime import UTC, datetime

import pytest

from billing.subscriptions import (
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from core.exceptions import TutorNotFoundError
from core.models import Contact, Level, PriceSort, Tag, TutorStatus, WorkFormat
from infra.subscriptions import SubscriptionsPg
from infra.tutor_filter import TutorFilterPg
from infra.users import UsersPg
from tests.conftest import seed_tutor, seed_tutor_user


async def _link_active_subscription(
    db_connection,
    tutor_id,
    plan_id: SubscriptionPlanId = SubscriptionPlanId.BASE,
) -> None:
    users = UsersPg(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)
    user = await seed_tutor_user(db_connection)
    await users.link_tutor(user.id, tutor_id)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        ),
    )


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
    approved = await seed_tutor(
        db_connection,
        description="Approved tutor",
        price=1000,
        status=TutorStatus.APPROVED,
        tag_names=["grammar"],
    )
    await _link_active_subscription(db_connection, approved.id)
    await seed_tutor(
        db_connection,
        description="Draft tutor",
        price=1000,
        status=TutorStatus.DRAFT,
        tag_names=["grammar"],
    )
    await seed_tutor(
        db_connection,
        description="Approved without subscription",
        price=1000,
        status=TutorStatus.APPROVED,
        tag_names=["grammar"],
    )
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.filter(page=1, page_size=10)

    assert len(profiles) == 1
    assert profiles[0].description == "Approved tutor"
    assert profiles[0].status == TutorStatus.APPROVED


@pytest.mark.asyncio
async def test_filter_by_price_levels_cities_and_tags(db_connection):
    match = await seed_tutor(
        db_connection,
        description="Match",
        cities=["Moscow"],
        levels=[Level.A1, Level.B2],
        price=1500,
        work_format=WorkFormat.ONLINE,
        tag_names=["grammar", "speaking"],
        status=TutorStatus.APPROVED,
    )
    await _link_active_subscription(db_connection, match.id)
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


@pytest.mark.asyncio
async def test_filter_pro_only_returns_tutors_with_active_pro(db_connection):
    pro_tutor = await seed_tutor(
        db_connection,
        description="PRO tutor",
        status=TutorStatus.APPROVED,
    )
    base_tutor = await seed_tutor(
        db_connection,
        description="BASE tutor",
        status=TutorStatus.APPROVED,
    )
    await seed_tutor(
        db_connection,
        description="No subscription",
        status=TutorStatus.APPROVED,
    )

    users = UsersPg(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)

    pro_user = await seed_tutor_user(db_connection)
    await users.link_tutor(pro_user.id, pro_tutor.id)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=pro_user.id,
            plan_id=SubscriptionPlanId.PRO,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        ),
    )

    base_user = await seed_tutor_user(db_connection)
    await users.link_tutor(base_user.id, base_tutor.id)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=base_user.id,
            plan_id=SubscriptionPlanId.BASE,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        ),
    )

    tutor_filter = TutorFilterPg(db_connection)
    profiles = await tutor_filter.filter(pro_only=True, page=1, page_size=10)

    assert len(profiles) == 1
    assert profiles[0].id == pro_tutor.id
    assert profiles[0].description == "PRO tutor"


@pytest.mark.asyncio
async def test_filter_sorts_by_price_asc(db_connection):
    cheap = await seed_tutor(
        db_connection,
        description="Cheap",
        price=1000,
        status=TutorStatus.APPROVED,
    )
    expensive = await seed_tutor(
        db_connection,
        description="Expensive",
        price=5000,
        status=TutorStatus.APPROVED,
    )
    mid = await seed_tutor(
        db_connection,
        description="Mid",
        price=2500,
        status=TutorStatus.APPROVED,
    )
    await _link_active_subscription(db_connection, cheap.id)
    await _link_active_subscription(db_connection, expensive.id)
    await _link_active_subscription(db_connection, mid.id)
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.filter(
        price_sort=PriceSort.ASC,
        page=1,
        page_size=10,
    )

    assert [profile.price for profile in profiles] == [1000, 2500, 5000]


@pytest.mark.asyncio
async def test_filter_sorts_by_price_desc(db_connection):
    cheap = await seed_tutor(
        db_connection,
        description="Cheap",
        price=1000,
        status=TutorStatus.APPROVED,
    )
    expensive = await seed_tutor(
        db_connection,
        description="Expensive",
        price=5000,
        status=TutorStatus.APPROVED,
    )
    mid = await seed_tutor(
        db_connection,
        description="Mid",
        price=2500,
        status=TutorStatus.APPROVED,
    )
    await _link_active_subscription(db_connection, cheap.id)
    await _link_active_subscription(db_connection, expensive.id)
    await _link_active_subscription(db_connection, mid.id)
    tutor_filter = TutorFilterPg(db_connection)

    profiles = await tutor_filter.filter(
        price_sort=PriceSort.DESC,
        page=1,
        page_size=10,
    )

    assert [profile.price for profile in profiles] == [5000, 2500, 1000]


@pytest.mark.asyncio
async def test_filter_pro_only_excludes_past_due_pro(db_connection):
    past_due_tutor = await seed_tutor(
        db_connection,
        description="Past due PRO",
        status=TutorStatus.APPROVED,
    )
    users = UsersPg(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)
    user = await seed_tutor_user(db_connection)
    await users.link_tutor(user.id, past_due_tutor.id)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=SubscriptionPlanId.PRO,
            status=SubscriptionStatus.PAST_DUE,
            period_start=now,
            period_end=now,
            paid_at=now,
        ),
    )

    tutor_filter = TutorFilterPg(db_connection)
    profiles = await tutor_filter.filter(pro_only=True, page=1, page_size=10)

    assert profiles == []
