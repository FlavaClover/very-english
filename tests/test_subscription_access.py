from datetime import UTC, datetime

import pytest

from api.access_policy import RequiredSubscription
from api.middlewares.subscription_gate import (
    ProPlanRequiredError,
    SubscriptionAccessMiddleware,
    SubscriptionRequiredError,
)
from billing.subscriptions import (
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from infra.subscriptions import SubscriptionsPg
from tests.conftest import seed_tutor_user


@pytest.mark.asyncio
async def test_subscription_gate_requires_active_plan(db_connection):
    user = await seed_tutor_user(db_connection)
    middleware = SubscriptionAccessMiddleware(None, db_connection.engine)

    with pytest.raises(SubscriptionRequiredError):
        await middleware._enforce(
            db_connection,
            user.id,
            RequiredSubscription.PRO,
        )


@pytest.mark.asyncio
async def test_subscription_gate_requires_pro_plan(db_connection):
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
    middleware = SubscriptionAccessMiddleware(None, db_connection.engine)

    with pytest.raises(ProPlanRequiredError):
        await middleware._enforce(
            db_connection,
            user.id,
            RequiredSubscription.PRO,
        )
