import calendar
import logging
import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core.subscriptions import (
    AbstractSubscriptionService,
    CheckoutResult,
    PaymentEventType,
    PaymentGateway,
    PaymentRecord,
    PaymentRepository,
    PaymentStatus,
    SubscriptionPeriodHistory,
    SubscriptionPlanId,
    SubscriptionRepository,
    SubscriptionStatus,
    UpgradeQuote,
    UserSubscription,
    YooKassaPaymentResult,
    YooKassaPaymentStatus,
)

logger = logging.getLogger(__name__)


class SubscriptionNotFoundError(Exception):
    """У тутора нет активной подписки."""


class InvalidPlanError(Exception):
    """Некорректный или недоступный тарифный план."""


class InvalidSubscriptionStateError(Exception):
    """Операция недоступна в текущем состоянии подписки."""


class SubscriptionService(AbstractSubscriptionService):
    def __init__(
        self,
        payments: PaymentRepository,
        subscriptions: SubscriptionRepository,
        gateway: PaymentGateway,
    ) -> None:
        self._payments = payments
        self._subscriptions = subscriptions
        self._gateway = gateway

    async def list_plans(self):
        return await self._subscriptions.list_plans()

    async def get_active_subscription(self, user_id: UUID) -> UserSubscription | None:
        return await self._subscriptions.get_active(user_id)

    async def list_history(self, user_id: UUID, limit: int, offset: int):
        return await self._subscriptions.list_history(user_id, limit, offset)

    async def list_payments(self, user_id: UUID, limit: int, offset: int):
        return await self._payments.list_by_user(user_id, limit, offset)

    async def checkout(
        self,
        user_id: UUID,
        plan_id: SubscriptionPlanId,
        return_url: str,
    ) -> CheckoutResult:
        plan = await self._subscriptions.get_plan(plan_id)
        if plan is None:
            raise InvalidPlanError(f"Unknown plan: {plan_id.value}")

        payment_id = uuid4()
        idempotence_key = str(uuid4())
        payment = PaymentRecord(
            id=payment_id,
            user_id=user_id,
            plan_id=plan_id,
            event_type=PaymentEventType.INITIAL,
            amount_rub=plan.price_rub,
            status=PaymentStatus.PENDING,
            idempotence_key=idempotence_key,
        )
        await self._payments.create(payment)

        metadata = self._payment_metadata(payment)
        result = await self._gateway.create_checkout_payment(
            amount_rub=plan.price_rub,
            description=f"Подписка {plan_id.value.upper()}",
            idempotence_key=idempotence_key,
            return_url=return_url,
            metadata=metadata,
            save_payment_method=True,
        )
        await self._payments.set_yookassa_payment_id(
            payment_id,
            result.yookassa_payment_id,
        )
        logger.info(
            "Checkout created: user_id=%s plan=%s payment_id=%s amount_rub=%s "
            "yookassa_id=%s status=%s",
            user_id,
            plan_id.value,
            payment_id,
            plan.price_rub,
            result.yookassa_payment_id,
            result.status.value,
        )

        return CheckoutResult(
            payment_id=payment_id,
            confirmation_url=result.confirmation_url,
        )

    async def get_upgrade_quote(
        self,
        user_id: UUID,
        now: datetime | None = None,
    ) -> UpgradeQuote:
        now = now or datetime.now(UTC)
        subscription = await self._subscriptions.get_active(user_id)
        if subscription is None or subscription.status is not SubscriptionStatus.ACTIVE:
            raise SubscriptionNotFoundError("Active subscription required for upgrade")

        if subscription.plan_id is not SubscriptionPlanId.BASE:
            raise InvalidSubscriptionStateError(
                "Upgrade is available only from BASE plan"
            )

        base_plan = await self._subscriptions.get_plan(SubscriptionPlanId.BASE)
        pro_plan = await self._subscriptions.get_plan(SubscriptionPlanId.PRO)
        if base_plan is None or pro_plan is None:
            raise InvalidPlanError("Subscription plans are not configured")

        amount_rub = self._calculate_upgrade_amount_rub(
            base_plan.price_rub,
            pro_plan.price_rub,
            subscription.period_start,
            subscription.period_end,
            now,
        )
        return UpgradeQuote(
            amount_rub=amount_rub,
            requires_payment=amount_rub > 0,
            period_start=subscription.period_start,
            period_end=subscription.period_end,
        )

    async def upgrade(
        self,
        user_id: UUID,
        return_url: str,
        now: datetime | None = None,
    ) -> CheckoutResult:
        now = now or datetime.now(UTC)
        quote = await self.get_upgrade_quote(user_id, now)
        subscription = await self._subscriptions.get_active(user_id)
        if subscription is None:
            raise SubscriptionNotFoundError("Active subscription required for upgrade")

        if not quote.requires_payment:
            await self._subscriptions.upsert_active(
                UserSubscription(
                    user_id=user_id,
                    plan_id=SubscriptionPlanId.PRO,
                    status=SubscriptionStatus.ACTIVE,
                    period_start=subscription.period_start,
                    period_end=subscription.period_end,
                    paid_at=subscription.paid_at,
                    yookassa_payment_method_id=subscription.yookassa_payment_method_id,
                )
            )
            logger.info(
                "Upgrade applied without payment: user_id=%s plan=pro amount_rub=0",
                user_id,
            )
            return CheckoutResult(payment_id=uuid4(), confirmation_url=None)

        amount_rub = quote.amount_rub
        payment_id = uuid4()
        idempotence_key = str(uuid4())
        payment = PaymentRecord(
            id=payment_id,
            user_id=user_id,
            plan_id=SubscriptionPlanId.PRO,
            event_type=PaymentEventType.UPGRADE,
            amount_rub=amount_rub,
            status=PaymentStatus.PENDING,
            idempotence_key=idempotence_key,
        )
        await self._payments.create(payment)

        metadata = self._payment_metadata(payment)
        result = await self._gateway.create_checkout_payment(
            amount_rub=amount_rub,
            description="Upgrade to PRO",
            idempotence_key=idempotence_key,
            return_url=return_url,
            metadata=metadata,
            save_payment_method=True,
        )
        await self._payments.set_yookassa_payment_id(
            payment_id,
            result.yookassa_payment_id,
        )
        logger.info(
            "Upgrade checkout created: user_id=%s payment_id=%s amount_rub=%s "
            "yookassa_id=%s status=%s",
            user_id,
            payment_id,
            amount_rub,
            result.yookassa_payment_id,
            result.status.value,
        )

        return CheckoutResult(
            payment_id=payment_id,
            confirmation_url=result.confirmation_url,
        )

    async def run_renewal_batch(self) -> None:
        """Продлевает подписки с истёкшим периодом и помечает просроченные."""
        due = await self._subscriptions.list_due_for_renewal(100)
        expired = await self._subscriptions.list_expired_without_autopayment(100)
        logger.info(
            "Renewal batch started: due_for_renewal=%d expired_without_autopayment=%d",
            len(due),
            len(expired),
        )
        for subscription in due:
            await self.renew_subscription(subscription)

        for subscription in expired:
            await self.expire_without_autopayment(subscription)

        logger.info(
            "Renewal batch finished: processed_renewals=%d marked_expired=%d",
            len(due),
            len(expired),
        )

    async def run_payment_sync_batch(self) -> None:
        """Синхронизирует pending-платежи со статусами в ЮKassa."""
        pending = await self._payments.list_pending_for_sync(100)
        logger.info("Payment sync batch started: pending=%d", len(pending))
        for payment in pending:
            await self.sync_payment_status(payment)
        logger.info("Payment sync batch finished: checked=%d", len(pending))

    async def renew_subscription(self, subscription: UserSubscription) -> None:
        if subscription.yookassa_payment_method_id is None:
            logger.warning(
                "Skip renewal for user %s: no payment method",
                subscription.user_id,
            )
            return

        plan = await self._subscriptions.get_plan(subscription.plan_id)
        if plan is None:
            raise InvalidPlanError(f"Unknown plan: {subscription.plan_id.value}")

        payment_id = uuid4()
        idempotence_key = str(uuid4())
        payment = PaymentRecord(
            id=payment_id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            event_type=PaymentEventType.RENEWAL,
            amount_rub=plan.price_rub,
            status=PaymentStatus.PENDING,
            idempotence_key=idempotence_key,
        )
        await self._payments.create(payment)

        metadata = self._payment_metadata(payment)
        result = await self._gateway.create_autopayment(
            amount_rub=plan.price_rub,
            description=f"Renewal {subscription.plan_id.value.upper()}",
            idempotence_key=idempotence_key,
            payment_method_id=subscription.yookassa_payment_method_id,
            metadata=metadata,
        )
        await self._payments.set_yookassa_payment_id(
            payment_id,
            result.yookassa_payment_id,
        )
        logger.info(
            "Renewal payment created: user_id=%s plan=%s payment_id=%s amount_rub=%s "
            "yookassa_id=%s status=%s",
            subscription.user_id,
            subscription.plan_id.value,
            payment_id,
            plan.price_rub,
            result.yookassa_payment_id,
            result.status.value,
        )
        if result.status in {
            YooKassaPaymentStatus.SUCCEEDED,
            YooKassaPaymentStatus.CANCELED,
        }:
            await self.process_payment_outcome(payment_id, result)

    async def expire_without_autopayment(self, subscription: UserSubscription) -> None:
        await self._subscriptions.set_status(
            subscription.user_id,
            SubscriptionStatus.EXPIRED,
        )
        logger.info(
            "Subscription expired (no autopayment): user_id=%s plan=%s",
            subscription.user_id,
            subscription.plan_id.value,
        )

    async def handle_webhook(self, payload: dict) -> None:
        event_object = payload.get("object") or {}
        yookassa_payment_id = event_object.get("id")
        event_name = payload.get("event")
        if yookassa_payment_id is None:
            logger.warning("Webhook without payment id: %s", payload)
            return

        logger.info(
            "YooKassa webhook received: event=%s yookassa_id=%s status=%s",
            event_name,
            yookassa_payment_id,
            event_object.get("status"),
        )

        payment = await self._payments.get_by_yookassa_id(str(yookassa_payment_id))
        if payment is None:
            metadata = event_object.get("metadata") or {}
            payment_id_raw = metadata.get("payment_id")
            if payment_id_raw is not None:
                payment = await self._payments.get(UUID(str(payment_id_raw)))

        if payment is None:
            logger.warning(
                "Payment not found for webhook yookassa id %s",
                yookassa_payment_id,
            )
            return

        result = self._result_from_webhook_object(event_object)
        logger.info(
            "YooKassa webhook matched payment: payment_id=%s user_id=%s event_type=%s",
            payment.id,
            payment.user_id,
            payment.event_type.value,
        )
        await self.process_payment_outcome(payment.id, result)

    async def sync_payment_status(self, payment: PaymentRecord) -> None:
        if payment.yookassa_payment_id is None:
            return
        result = await self._gateway.get_payment(payment.yookassa_payment_id)
        if result.status in {
            YooKassaPaymentStatus.PENDING,
            YooKassaPaymentStatus.WAITING_FOR_CAPTURE,
        }:
            return
        logger.info(
            "Payment status synced from YooKassa: payment_id=%s yookassa_id=%s status=%s",
            payment.id,
            payment.yookassa_payment_id,
            result.status.value,
        )
        await self.process_payment_outcome(payment.id, result)

    async def process_payment_outcome(
        self,
        payment_id: UUID,
        result: YooKassaPaymentResult,
    ) -> None:
        payment = await self._payments.get(payment_id)
        if payment is None:
            logger.warning("Payment %s not found for outcome processing", payment_id)
            return

        if payment.status is PaymentStatus.SUCCEEDED:
            logger.info(
                "Payment already processed, skipping: payment_id=%s user_id=%s",
                payment_id,
                payment.user_id,
            )
            return

        if result.status is YooKassaPaymentStatus.SUCCEEDED:
            paid_at = datetime.now(UTC)
            await self._payments.update_status(
                payment_id,
                PaymentStatus.SUCCEEDED,
                paid_at=paid_at,
                yookassa_payment_method_id=result.payment_method_id,
            )
            if not await self._subscriptions.history_exists_for_payment(payment_id):
                logger.info(
                    "Payment succeeded: payment_id=%s user_id=%s event_type=%s amount_rub=%s",
                    payment_id,
                    payment.user_id,
                    payment.event_type.value,
                    payment.amount_rub,
                )
                await self._apply_successful_payment(payment, paid_at, result)
            else:
                logger.info(
                    "Payment succeeded but history exists: payment_id=%s user_id=%s",
                    payment_id,
                    payment.user_id,
                )
            return

        if result.status is YooKassaPaymentStatus.CANCELED:
            await self._payments.update_status(
                payment_id,
                PaymentStatus.CANCELED,
                cancellation_details=result.cancellation_details,
            )
            logger.info(
                "Payment canceled: payment_id=%s user_id=%s event_type=%s reason=%s",
                payment_id,
                payment.user_id,
                payment.event_type.value,
                result.cancellation_details,
            )
            if payment.event_type is PaymentEventType.RENEWAL:
                await self._subscriptions.set_status(
                    payment.user_id,
                    SubscriptionStatus.PAST_DUE,
                )
                logger.info(
                    "Subscription marked past_due after renewal failure: user_id=%s",
                    payment.user_id,
                )

    async def _apply_successful_payment(
        self,
        payment: PaymentRecord,
        paid_at: datetime,
        result: YooKassaPaymentResult,
    ) -> None:
        existing = await self._subscriptions.get_active(payment.user_id)

        if payment.event_type is PaymentEventType.UPGRADE:
            if existing is None:
                logger.warning(
                    "Upgrade payment succeeded but active subscription missing: "
                    "payment_id=%s user_id=%s",
                    payment.id,
                    payment.user_id,
                )
                return
            period_start = existing.period_start
            period_end = existing.period_end
            plan_id = SubscriptionPlanId.PRO
        elif payment.event_type is PaymentEventType.RENEWAL:
            period_start = paid_at
            period_end = self._add_billing_month(period_start)
            plan_id = payment.plan_id
        else:
            period_start = paid_at
            period_end = self._add_billing_month(period_start)
            plan_id = payment.plan_id

        await self._subscriptions.upsert_active(
            UserSubscription(
                user_id=payment.user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                period_start=period_start,
                period_end=period_end,
                paid_at=paid_at,
                yookassa_payment_method_id=result.payment_method_id
                or (existing.yookassa_payment_method_id if existing else None),
            )
        )
        await self._subscriptions.append_history(
            SubscriptionPeriodHistory(
                id=uuid4(),
                user_id=payment.user_id,
                payment_id=payment.id,
                plan_id=plan_id,
                event_type=payment.event_type,
                period_start=period_start,
                period_end=period_end,
                paid_at=paid_at,
            )
        )
        logger.info(
            "Subscription updated: user_id=%s plan=%s event_type=%s "
            "period_start=%s period_end=%s payment_id=%s",
            payment.user_id,
            plan_id.value,
            payment.event_type.value,
            period_start.isoformat(),
            period_end.isoformat(),
            payment.id,
        )

    @staticmethod
    def _add_billing_month(start: datetime) -> datetime:
        """Добавляет один календарный месяц к моменту начала периода."""
        month = start.month + 1
        year = start.year
        if month > 12:
            month = 1
            year += 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(start.day, max_day)
        return start.replace(
            year=year,
            month=month,
            day=day,
            hour=start.hour,
            minute=start.minute,
            second=start.second,
            microsecond=start.microsecond,
        )

    @staticmethod
    def _calculate_upgrade_amount_rub(
        base_price_rub: int,
        pro_price_rub: int,
        period_start: datetime,
        period_end: datetime,
        now: datetime,
    ) -> int:
        """Считает доплату за переход BASE→PRO за оставшиеся дни периода.

        :param base_price_rub: Цена BASE за месяц.
        :param pro_price_rub: Цена PRO за месяц.
        :param period_start: Начало текущего оплаченного периода.
        :param period_end: Конец текущего оплаченного периода.
        :param now: Текущий момент времени.
        :return: Сумма доплаты в рублях.
        """
        if pro_price_rub <= base_price_rub:
            return 0

        remaining_seconds = (period_end - now).total_seconds()
        if remaining_seconds <= 0:
            return 0

        period_seconds = (period_end - period_start).total_seconds()
        if period_seconds <= 0:
            return 0

        remaining_days = max(1, math.ceil(remaining_seconds / 86400))
        period_days = max(1, math.ceil(period_seconds / 86400))
        delta = pro_price_rub - base_price_rub
        return max(0, round(delta * remaining_days / period_days))

    @staticmethod
    def _payment_metadata(payment: PaymentRecord) -> dict[str, str]:
        return {
            "payment_id": str(payment.id),
            "user_id": str(payment.user_id),
            "plan_id": payment.plan_id.value,
            "event_type": payment.event_type.value,
        }

    @staticmethod
    def _result_from_webhook_object(event_object: dict) -> YooKassaPaymentResult:
        payment_method = event_object.get("payment_method") or {}
        cancellation = event_object.get("cancellation_details") or {}
        return YooKassaPaymentResult(
            yookassa_payment_id=str(event_object.get("id", "")),
            status=YooKassaPaymentStatus.from_api_value(
                str(event_object.get("status", "")),
            ),
            payment_method_id=payment_method.get("id"),
            cancellation_details=cancellation.get("reason"),
        )
