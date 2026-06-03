from uuid import uuid4

import pytest

from core.subscriptions import (
    PaymentEventType,
    PaymentRecord,
    PaymentStatus,
    SubscriptionPlanId,
    YooKassaPaymentResult,
    YooKassaPaymentStatus,
)
from infra.payments import PaymentsPg
from infra.subscriptions import SubscriptionsPg
from services.subscription_service import SubscriptionService
from tests.conftest import seed_tutor_user


class FakeGateway:
    async def create_checkout_payment(self, **kwargs):
        raise NotImplementedError

    async def create_autopayment(self, **kwargs):
        raise NotImplementedError

    async def get_payment(self, yookassa_payment_id: str):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_process_payment_outcome_idempotent(db_connection):
    user = await seed_tutor_user(db_connection)
    payments = PaymentsPg(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    service = SubscriptionService(payments, subscriptions, FakeGateway())

    payment_id = uuid4()
    payment = PaymentRecord(
        id=payment_id,
        user_id=user.id,
        plan_id=SubscriptionPlanId.BASE,
        event_type=PaymentEventType.INITIAL,
        amount_rub=990,
        status=PaymentStatus.PENDING,
        idempotence_key=str(uuid4()),
        yookassa_payment_id="yk-1",
    )
    await payments.create(payment)

    result = YooKassaPaymentResult(
        yookassa_payment_id="yk-1",
        status=YooKassaPaymentStatus.SUCCEEDED,
        payment_method_id="pm-1",
    )
    await service.process_payment_outcome(payment_id, result)
    await service.process_payment_outcome(payment_id, result)

    active = await subscriptions.get_active(user.id)
    assert active is not None
    assert active.plan_id is SubscriptionPlanId.BASE

    history = await subscriptions.list_history(user.id, 10, 0)
    assert len(history) == 1
