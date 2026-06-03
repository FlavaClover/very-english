from datetime import UTC, datetime

import pytest

from core.subscriptions import SubscriptionPlanId, SubscriptionStatus, UserSubscription
from infra.payments import PaymentsPg
from infra.subscriptions import SubscriptionsPg
from services.subscription_service import (
    InvalidSubscriptionStateError,
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
async def test_checkout_rejects_active_subscription(db_connection):
    user = await seed_tutor_user(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)
    await subscriptions.upsert_active(
        UserSubscription(
            user_id=user.id,
            plan_id=SubscriptionPlanId.BASE,
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
            paid_at=now,
        )
    )
    service = SubscriptionService(
        PaymentsPg(db_connection),
        subscriptions,
        FakeGateway(),
    )

    with pytest.raises(InvalidSubscriptionStateError):
        await service.checkout(
            user_id=user.id,
            plan_id=SubscriptionPlanId.PRO,
            return_url="https://example.com/return",
        )
