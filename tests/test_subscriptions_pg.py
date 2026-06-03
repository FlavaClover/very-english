from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.subscriptions import (
    PaymentEventType,
    PaymentRecord,
    PaymentStatus,
    SubscriptionPeriodHistory,
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from infra.payments import PaymentsPg
from infra.subscriptions import SubscriptionsPg
from tests.conftest import seed_tutor_user


@pytest.mark.asyncio
async def test_upsert_active_and_history(db_connection):
    user = await seed_tutor_user(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    now = datetime.now(UTC)

    subscription = UserSubscription(
        user_id=user.id,
        plan_id=SubscriptionPlanId.BASE,
        status=SubscriptionStatus.ACTIVE,
        period_start=now,
        period_end=now,
        paid_at=now,
        yookassa_payment_method_id="pm-1",
    )
    await subscriptions.upsert_active(subscription)

    active = await subscriptions.get_active(user.id)
    assert active is not None
    assert active.plan_id is SubscriptionPlanId.BASE

    payment_id = uuid4()
    payments = PaymentsPg(db_connection)
    await payments.create(
        PaymentRecord(
            id=payment_id,
            user_id=user.id,
            plan_id=SubscriptionPlanId.BASE,
            event_type=PaymentEventType.INITIAL,
            amount_rub=990,
            status=PaymentStatus.SUCCEEDED,
            idempotence_key=str(uuid4()),
        )
    )
    await subscriptions.append_history(
        SubscriptionPeriodHistory(
            id=uuid4(),
            user_id=user.id,
            payment_id=payment_id,
            plan_id=SubscriptionPlanId.BASE,
            event_type=PaymentEventType.INITIAL,
            period_start=now,
            period_end=now,
            paid_at=now,
        )
    )
    assert await subscriptions.history_exists_for_payment(payment_id) is True

    history = await subscriptions.list_history(user.id, 10, 0)
    assert len(history) == 1
    assert history[0].payment_id == payment_id


@pytest.mark.asyncio
async def test_list_plans(db_connection):
    subscriptions = SubscriptionsPg(db_connection)
    plans = await subscriptions.list_plans()
    plan_ids = {plan.id for plan in plans}
    assert SubscriptionPlanId.BASE in plan_ids
    assert SubscriptionPlanId.PRO in plan_ids
