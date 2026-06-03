from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.subscriptions import (
    PaymentEventType,
    PaymentRecord,
    PaymentStatus,
    SubscriptionPlanId,
)
from infra.payments import PaymentsPg
from tests.conftest import seed_tutor_user


@pytest.mark.asyncio
async def test_create_and_update_payment(db_connection):
    user = await seed_tutor_user(db_connection)
    payments = PaymentsPg(db_connection)

    payment = PaymentRecord(
        id=uuid4(),
        user_id=user.id,
        plan_id=SubscriptionPlanId.BASE,
        event_type=PaymentEventType.INITIAL,
        amount_rub=990,
        status=PaymentStatus.PENDING,
        idempotence_key=str(uuid4()),
    )
    created = await payments.create(payment)
    assert created.status is PaymentStatus.PENDING

    await payments.set_yookassa_payment_id(created.id, "yk-test-1")
    fetched = await payments.get_by_yookassa_id("yk-test-1")
    assert fetched is not None
    assert fetched.id == created.id

    paid_at = datetime.now(UTC)
    await payments.update_status(
        created.id,
        PaymentStatus.SUCCEEDED,
        paid_at=paid_at,
        yookassa_payment_method_id="pm-test",
    )
    updated = await payments.get(created.id)
    assert updated is not None
    assert updated.status is PaymentStatus.SUCCEEDED
    assert updated.paid_at == paid_at


@pytest.mark.asyncio
async def test_list_pending_for_sync(db_connection):
    user = await seed_tutor_user(db_connection)
    payments = PaymentsPg(db_connection)

    old_payment = PaymentRecord(
        id=uuid4(),
        user_id=user.id,
        plan_id=SubscriptionPlanId.BASE,
        event_type=PaymentEventType.INITIAL,
        amount_rub=990,
        status=PaymentStatus.PENDING,
        idempotence_key=str(uuid4()),
        yookassa_payment_id="yk-old",
    )
    await payments.create(old_payment)
    await db_connection.execute(
        __import__("sqlalchemy").text(
            "UPDATE payments SET created_at = NOW() - INTERVAL '5 minutes' WHERE id = :id"
        ),
        {"id": old_payment.id},
    )

    pending = await payments.list_pending_for_sync(10)
    assert any(item.id == old_payment.id for item in pending)
