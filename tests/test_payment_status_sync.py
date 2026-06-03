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


class SyncGateway:
    def __init__(self, status: YooKassaPaymentStatus) -> None:
        self.status = status

    async def create_checkout_payment(self, **kwargs):
        raise NotImplementedError

    async def create_autopayment(self, **kwargs):
        raise NotImplementedError

    async def get_payment(self, yookassa_payment_id: str) -> YooKassaPaymentResult:
        return YooKassaPaymentResult(
            yookassa_payment_id=yookassa_payment_id,
            status=self.status,
            payment_method_id="pm-sync",
        )


@pytest.mark.asyncio
async def test_sync_payment_status_applies_outcome(db_connection):
    user = await seed_tutor_user(db_connection)
    payments = PaymentsPg(db_connection)
    subscriptions = SubscriptionsPg(db_connection)
    service = SubscriptionService(
        payments, subscriptions, SyncGateway(YooKassaPaymentStatus.SUCCEEDED)
    )

    payment = PaymentRecord(
        id=uuid4(),
        user_id=user.id,
        plan_id=SubscriptionPlanId.PRO,
        event_type=PaymentEventType.INITIAL,
        amount_rub=1990,
        status=PaymentStatus.PENDING,
        idempotence_key=str(uuid4()),
        yookassa_payment_id="yk-sync",
    )
    await payments.create(payment)
    await db_connection.execute(
        __import__("sqlalchemy").text(
            "UPDATE payments SET created_at = NOW() - INTERVAL '5 minutes' WHERE id = :id"
        ),
        {"id": payment.id},
    )

    await service.sync_payment_status(payment)

    updated = await payments.get(payment.id)
    assert updated is not None
    assert updated.status is PaymentStatus.SUCCEEDED
    assert await subscriptions.get_active(user.id) is not None
