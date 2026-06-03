from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.subscriptions import (
    PaymentEventType,
    PaymentRecord,
    PaymentRepository,
    PaymentStatus,
    SubscriptionPlanId,
)


class PaymentsPg(PaymentRepository):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    def _row_to_payment(self, row) -> PaymentRecord:
        return PaymentRecord(
            id=row["id"],
            user_id=row["user_id"],
            plan_id=SubscriptionPlanId(str(row["plan_id"])),
            event_type=PaymentEventType(str(row["event_type"])),
            amount_rub=row["amount_rub"],
            status=PaymentStatus(str(row["status"])),
            idempotence_key=row["idempotence_key"],
            yookassa_payment_id=row["yookassa_payment_id"],
            yookassa_payment_method_id=row["yookassa_payment_method_id"],
            cancellation_details=row["cancellation_details"],
            paid_at=row["paid_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def create(self, payment: PaymentRecord) -> PaymentRecord:
        await self._connection.execute(
            text(
                """
                INSERT INTO payments (
                    id,
                    user_id,
                    plan_id,
                    event_type,
                    amount_rub,
                    status,
                    idempotence_key,
                    yookassa_payment_id,
                    yookassa_payment_method_id,
                    cancellation_details,
                    paid_at
                )
                VALUES (
                    :id,
                    :user_id,
                    CAST(:plan_id AS subscription_plan),
                    CAST(:event_type AS payment_event_type),
                    :amount_rub,
                    CAST(:status AS payment_status),
                    :idempotence_key,
                    :yookassa_payment_id,
                    :yookassa_payment_method_id,
                    :cancellation_details,
                    :paid_at
                )
                """
            ),
            dict(
                id=payment.id,
                user_id=payment.user_id,
                plan_id=payment.plan_id.value,
                event_type=payment.event_type.value,
                amount_rub=payment.amount_rub,
                status=payment.status.value,
                idempotence_key=payment.idempotence_key,
                yookassa_payment_id=payment.yookassa_payment_id,
                yookassa_payment_method_id=payment.yookassa_payment_method_id,
                cancellation_details=payment.cancellation_details,
                paid_at=payment.paid_at,
            ),
        )
        return payment

    async def get(self, payment_id: UUID) -> PaymentRecord | None:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    user_id,
                    plan_id::text AS plan_id,
                    event_type::text AS event_type,
                    amount_rub,
                    status::text AS status,
                    idempotence_key,
                    yookassa_payment_id,
                    yookassa_payment_method_id,
                    cancellation_details,
                    paid_at,
                    created_at,
                    updated_at
                FROM payments
                WHERE id = :payment_id
                """
            ),
            dict(payment_id=payment_id),
        )
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_payment(row)

    async def get_by_yookassa_id(
        self, yookassa_payment_id: str
    ) -> PaymentRecord | None:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    user_id,
                    plan_id::text AS plan_id,
                    event_type::text AS event_type,
                    amount_rub,
                    status::text AS status,
                    idempotence_key,
                    yookassa_payment_id,
                    yookassa_payment_method_id,
                    cancellation_details,
                    paid_at,
                    created_at,
                    updated_at
                FROM payments
                WHERE yookassa_payment_id = :yookassa_payment_id
                """
            ),
            dict(yookassa_payment_id=yookassa_payment_id),
        )
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_payment(row)

    async def set_yookassa_payment_id(
        self,
        payment_id: UUID,
        yookassa_payment_id: str,
    ) -> None:
        await self._connection.execute(
            text(
                """
                UPDATE payments
                SET
                    yookassa_payment_id = :yookassa_payment_id,
                    updated_at = NOW()
                WHERE id = :payment_id
                """
            ),
            dict(payment_id=payment_id, yookassa_payment_id=yookassa_payment_id),
        )

    async def update_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        paid_at: datetime | None = None,
        yookassa_payment_method_id: str | None = None,
        cancellation_details: str | None = None,
    ) -> None:
        await self._connection.execute(
            text(
                """
                UPDATE payments
                SET
                    status = CAST(:status AS payment_status),
                    paid_at = COALESCE(:paid_at, paid_at),
                    yookassa_payment_method_id = COALESCE(
                        :yookassa_payment_method_id,
                        yookassa_payment_method_id
                    ),
                    cancellation_details = COALESCE(
                        :cancellation_details,
                        cancellation_details
                    ),
                    updated_at = NOW()
                WHERE id = :payment_id
                """
            ),
            dict(
                payment_id=payment_id,
                status=status.value,
                paid_at=paid_at,
                yookassa_payment_method_id=yookassa_payment_method_id,
                cancellation_details=cancellation_details,
            ),
        )

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PaymentRecord]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    user_id,
                    plan_id::text AS plan_id,
                    event_type::text AS event_type,
                    amount_rub,
                    status::text AS status,
                    idempotence_key,
                    yookassa_payment_id,
                    yookassa_payment_method_id,
                    cancellation_details,
                    paid_at,
                    created_at,
                    updated_at
                FROM payments
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            dict(user_id=user_id, limit=limit, offset=offset),
        )
        return [self._row_to_payment(row) for row in result.mappings()]

    async def list_pending_for_sync(self, limit: int) -> list[PaymentRecord]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    user_id,
                    plan_id::text AS plan_id,
                    event_type::text AS event_type,
                    amount_rub,
                    status::text AS status,
                    idempotence_key,
                    yookassa_payment_id,
                    yookassa_payment_method_id,
                    cancellation_details,
                    paid_at,
                    created_at,
                    updated_at
                FROM payments
                WHERE status = 'pending'
                  AND yookassa_payment_id IS NOT NULL
                  AND created_at < NOW() - INTERVAL '2 minutes'
                  AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at ASC
                LIMIT :limit
                """
            ),
            dict(limit=limit),
        )
        return [self._row_to_payment(row) for row in result.mappings()]
