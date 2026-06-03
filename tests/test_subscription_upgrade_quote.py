from datetime import UTC, datetime, timedelta

import pytest

from core.subscriptions import (
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from infra.payments import PaymentsPg
from infra.subscriptions import SubscriptionsPg
from services.subscription_service import (
    InvalidSubscriptionStateError,
    SubscriptionNotFoundError,
    SubscriptionService,
)
from tests.conftest import seed_tutor_user


class FakeGateway:
    async def create_checkout_payment(self, **kwargs):
        raise NotImplementedError

    async def create_autopayment(self, **kwargs):
        raise NotImplementedError

    async def get_payment(self, yookassa_payment_id: str):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_get_upgrade_quote_mid_period(db_connection):
    user = await seed_tutor_user(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime(2026, 1, 16, tzinfo=UTC)
    period_start = datetime(2026, 1, 1, tzinfo=UTC)
    period_end = datetime(2026, 2, 1, tzinfo=UTC)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=SubscriptionPlanId.BASE,
            status=SubscriptionStatus.ACTIVE,
            period_start=period_start,
            period_end=period_end,
            paid_at=period_start,
        )
    )
    service = SubscriptionService(
        PaymentsPg(db_connection), subscriptions, FakeGateway()
    )

    quote = await service.get_upgrade_quote(user.id, now=now)

    assert quote.amount_rub > 0
    assert quote.requires_payment is True
    assert quote.period_start == period_start
    assert quote.period_end == period_end


@pytest.mark.asyncio
async def test_get_upgrade_quote_after_period(db_connection):
    user = await seed_tutor_user(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    period_start = datetime(2026, 1, 1, tzinfo=UTC)
    period_end = datetime(2026, 2, 1, tzinfo=UTC)
    now = period_end + timedelta(days=1)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=SubscriptionPlanId.BASE,
            status=SubscriptionStatus.ACTIVE,
            period_start=period_start,
            period_end=period_end,
            paid_at=period_start,
        )
    )
    service = SubscriptionService(
        PaymentsPg(db_connection), subscriptions, FakeGateway()
    )

    quote = await service.get_upgrade_quote(user.id, now=now)

    assert quote.amount_rub == 0
    assert quote.requires_payment is False


@pytest.mark.asyncio
async def test_get_upgrade_quote_requires_base_plan(db_connection):
    user = await seed_tutor_user(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=SubscriptionPlanId.PRO,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        )
    )
    service = SubscriptionService(
        PaymentsPg(db_connection), subscriptions, FakeGateway()
    )

    with pytest.raises(InvalidSubscriptionStateError):
        await service.get_upgrade_quote(user.id)


@pytest.mark.asyncio
async def test_get_upgrade_quote_requires_active_subscription(db_connection):
    user = await seed_tutor_user(db_connection)
    service = SubscriptionService(
        PaymentsPg(db_connection), SubscriptionsPg(db_connection), FakeGateway()
    )

    with pytest.raises(SubscriptionNotFoundError):
        await service.get_upgrade_quote(user.id)
