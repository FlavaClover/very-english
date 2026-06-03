from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from billing.subscriptions import (
    PaymentEventType,
    PaymentStatus,
    SubscriptionPeriodHistory,
    SubscriptionPlan,
    SubscriptionPlanId,
    SubscriptionRepository,
    SubscriptionStatus,
    UserSubscription,
)


class SubscriptionsPg(SubscriptionRepository):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def list_plans(self) -> list[SubscriptionPlan]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    price_rub,
                    billing_interval
                FROM subscription_plans
                ORDER BY price_rub ASC
                """
            )
        )
        return [
            SubscriptionPlan(
                id=SubscriptionPlanId(str(row["id"])),
                price_rub=row["price_rub"],
                billing_interval=row["billing_interval"],
            )
            for row in result.mappings()
        ]

    async def get_plan(self, plan_id: SubscriptionPlanId) -> SubscriptionPlan | None:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    price_rub,
                    billing_interval
                FROM subscription_plans
                WHERE id = CAST(:plan_id AS subscription_plan)
                """
            ),
            dict(plan_id=plan_id.value),
        )
        row = result.mappings().first()
        if row is None:
            return None
        return SubscriptionPlan(
            id=SubscriptionPlanId(str(row["id"])),
            price_rub=row["price_rub"],
            billing_interval=row["billing_interval"],
        )

    def _row_to_subscription(self, row) -> UserSubscription:
        return UserSubscription(
            user_id=row["user_id"],
            plan_id=SubscriptionPlanId(str(row["plan_id"])),
            status=SubscriptionStatus(str(row["status"])),
            period_start=row["period_start"],
            period_end=row["period_end"],
            paid_at=row["paid_at"],
            yookassa_payment_method_id=row["yookassa_payment_method_id"],
            updated_at=row["updated_at"],
        )

    async def get_active(self, user_id: UUID) -> UserSubscription | None:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    user_id,
                    plan_id::text AS plan_id,
                    status::text AS status,
                    period_start,
                    period_end,
                    paid_at,
                    yookassa_payment_method_id,
                    updated_at
                FROM tutor_subscriptions
                WHERE user_id = :user_id
                """
            ),
            dict(user_id=user_id),
        )
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_subscription(row)

    async def upsert_active(self, subscription: UserSubscription) -> None:
        await self._connection.execute(
            text(
                """
                INSERT INTO tutor_subscriptions (
                    user_id,
                    plan_id,
                    status,
                    period_start,
                    period_end,
                    paid_at,
                    yookassa_payment_method_id,
                    updated_at
                )
                VALUES (
                    :user_id,
                    CAST(:plan_id AS subscription_plan),
                    CAST(:status AS subscription_status),
                    :period_start,
                    :period_end,
                    :paid_at,
                    :yookassa_payment_method_id,
                    NOW()
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    plan_id = EXCLUDED.plan_id,
                    status = EXCLUDED.status,
                    period_start = EXCLUDED.period_start,
                    period_end = EXCLUDED.period_end,
                    paid_at = EXCLUDED.paid_at,
                    yookassa_payment_method_id = COALESCE(
                        EXCLUDED.yookassa_payment_method_id,
                        tutor_subscriptions.yookassa_payment_method_id
                    ),
                    updated_at = NOW()
                """
            ),
            dict(
                user_id=subscription.user_id,
                plan_id=subscription.plan_id.value,
                status=subscription.status.value,
                period_start=subscription.period_start,
                period_end=subscription.period_end,
                paid_at=subscription.paid_at,
                yookassa_payment_method_id=subscription.yookassa_payment_method_id,
            ),
        )

    async def set_status(self, user_id: UUID, status: SubscriptionStatus) -> None:
        await self._connection.execute(
            text(
                """
                UPDATE tutor_subscriptions
                SET
                    status = CAST(:status AS subscription_status),
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            dict(user_id=user_id, status=status.value),
        )

    async def append_history(self, period: SubscriptionPeriodHistory) -> None:
        await self._connection.execute(
            text(
                """
                INSERT INTO tutor_subscription_history (
                    id,
                    user_id,
                    payment_id,
                    plan_id,
                    event_type,
                    period_start,
                    period_end,
                    paid_at
                )
                VALUES (
                    :id,
                    :user_id,
                    :payment_id,
                    CAST(:plan_id AS subscription_plan),
                    CAST(:event_type AS payment_event_type),
                    :period_start,
                    :period_end,
                    :paid_at
                )
                """
            ),
            dict(
                id=period.id,
                user_id=period.user_id,
                payment_id=period.payment_id,
                plan_id=period.plan_id.value,
                event_type=period.event_type.value,
                period_start=period.period_start,
                period_end=period.period_end,
                paid_at=period.paid_at,
            ),
        )

    async def history_exists_for_payment(self, payment_id: UUID) -> bool:
        result = await self._connection.execute(
            text(
                """
                SELECT 1
                FROM tutor_subscription_history
                WHERE payment_id = :payment_id
                """
            ),
            dict(payment_id=payment_id),
        )
        return result.first() is not None

    async def list_history(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SubscriptionPeriodHistory]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    h.id,
                    h.user_id,
                    h.payment_id,
                    h.plan_id::text AS plan_id,
                    h.event_type::text AS event_type,
                    h.period_start,
                    h.period_end,
                    h.paid_at,
                    p.amount_rub,
                    p.status::text AS payment_status
                FROM tutor_subscription_history h
                INNER JOIN payments p ON p.id = h.payment_id
                WHERE h.user_id = :user_id
                ORDER BY h.paid_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            dict(user_id=user_id, limit=limit, offset=offset),
        )
        return [
            SubscriptionPeriodHistory(
                id=row["id"],
                user_id=row["user_id"],
                payment_id=row["payment_id"],
                plan_id=SubscriptionPlanId(str(row["plan_id"])),
                event_type=PaymentEventType(str(row["event_type"])),
                period_start=row["period_start"],
                period_end=row["period_end"],
                paid_at=row["paid_at"],
                amount_rub=row["amount_rub"],
                payment_status=PaymentStatus(str(row["payment_status"])),
            )
            for row in result.mappings()
        ]

    async def list_due_for_renewal(self, limit: int) -> list[UserSubscription]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    ts.user_id,
                    ts.plan_id::text AS plan_id,
                    ts.status::text AS status,
                    ts.period_start,
                    ts.period_end,
                    ts.paid_at,
                    ts.yookassa_payment_method_id,
                    ts.updated_at
                FROM tutor_subscriptions ts
                INNER JOIN users u ON u.id = ts.user_id
                WHERE ts.status = 'active'
                  AND ts.period_end <= NOW()
                  AND u.autopayment_consent = TRUE
                  AND ts.yookassa_payment_method_id IS NOT NULL
                ORDER BY ts.period_end ASC
                LIMIT :limit
                """
            ),
            dict(limit=limit),
        )
        return [self._row_to_subscription(row) for row in result.mappings()]

    async def list_expired_without_autopayment(
        self, limit: int
    ) -> list[UserSubscription]:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    ts.user_id,
                    ts.plan_id::text AS plan_id,
                    ts.status::text AS status,
                    ts.period_start,
                    ts.period_end,
                    ts.paid_at,
                    ts.yookassa_payment_method_id,
                    ts.updated_at
                FROM tutor_subscriptions ts
                INNER JOIN users u ON u.id = ts.user_id
                WHERE ts.status = 'active'
                  AND ts.period_end <= NOW()
                  AND u.autopayment_consent = FALSE
                ORDER BY ts.period_end ASC
                LIMIT :limit
                """
            ),
            dict(limit=limit),
        )
        return [self._row_to_subscription(row) for row in result.mappings()]
