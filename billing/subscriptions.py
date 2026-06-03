from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class SubscriptionPlanId(Enum):
    BASE = "base"
    PRO = "pro"


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    EXPIRED = "expired"
    CANCELED = "canceled"


class PaymentEventType(Enum):
    INITIAL = "initial"
    RENEWAL = "renewal"
    UPGRADE = "upgrade"


class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class YooKassaPaymentStatus(Enum):
    """Статус платежа в API ЮKassa."""

    PENDING = "pending"
    WAITING_FOR_CAPTURE = "waiting_for_capture"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"

    @classmethod
    def from_api_value(cls, value: str) -> "YooKassaPaymentStatus":
        """Парсит статус из ответа или webhook ЮKassa.

        :param value: Значение поля ``status`` из API.
        :return: Статус платежа ЮKassa.
        :raises ValueError: Неизвестное значение статуса.
        """
        return cls(value)


@dataclass
class SubscriptionPlan:
    id: SubscriptionPlanId
    price_rub: int
    billing_interval: str


@dataclass
class PaymentRecord:
    id: UUID
    user_id: UUID
    plan_id: SubscriptionPlanId
    event_type: PaymentEventType
    amount_rub: int
    status: PaymentStatus
    idempotence_key: str
    yookassa_payment_id: str | None = None
    yookassa_payment_method_id: str | None = None
    cancellation_details: str | None = None
    paid_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class UserSubscription:
    user_id: UUID
    plan_id: SubscriptionPlanId
    status: SubscriptionStatus
    period_start: datetime
    period_end: datetime
    paid_at: datetime
    yookassa_payment_method_id: str | None = None
    updated_at: datetime | None = None


@dataclass
class SubscriptionPeriodHistory:
    id: UUID
    user_id: UUID
    payment_id: UUID
    plan_id: SubscriptionPlanId
    event_type: PaymentEventType
    period_start: datetime
    period_end: datetime
    paid_at: datetime
    amount_rub: int | None = None
    payment_status: PaymentStatus | None = None


@dataclass
class YooKassaPaymentResult:
    yookassa_payment_id: str
    status: YooKassaPaymentStatus
    confirmation_url: str | None = None
    payment_method_id: str | None = None
    cancellation_details: str | None = None


class PaymentGateway(ABC):
    @abstractmethod
    async def create_checkout_payment(
        self,
        amount_rub: int,
        description: str,
        idempotence_key: str,
        return_url: str,
        metadata: dict[str, str],
        save_payment_method: bool = True,
    ) -> YooKassaPaymentResult:
        """Создаёт платёж с redirect-подтверждением."""

    @abstractmethod
    async def create_autopayment(
        self,
        amount_rub: int,
        description: str,
        idempotence_key: str,
        payment_method_id: str,
        metadata: dict[str, str],
    ) -> YooKassaPaymentResult:
        """Создаёт безакцептный платёж по сохранённому методу."""

    @abstractmethod
    async def get_payment(self, yookassa_payment_id: str) -> YooKassaPaymentResult:
        """Возвращает актуальный статус платежа в ЮKassa."""


class PaymentRepository(ABC):
    @abstractmethod
    async def create(self, payment: PaymentRecord) -> PaymentRecord:
        """Сохраняет новый платёж."""

    @abstractmethod
    async def get(self, payment_id: UUID) -> PaymentRecord | None:
        """Возвращает платёж по внутреннему идентификатору."""

    @abstractmethod
    async def get_by_yookassa_id(
        self, yookassa_payment_id: str
    ) -> PaymentRecord | None:
        """Возвращает платёж по идентификатору ЮKassa."""

    @abstractmethod
    async def set_yookassa_payment_id(
        self,
        payment_id: UUID,
        yookassa_payment_id: str,
    ) -> None:
        """Привязывает идентификатор платежа ЮKassa."""

    @abstractmethod
    async def update_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        paid_at: datetime | None = None,
        yookassa_payment_method_id: str | None = None,
        cancellation_details: str | None = None,
    ) -> None:
        """Обновляет статус платежа."""

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PaymentRecord]:
        """Возвращает платежи пользователя-тутора."""

    @abstractmethod
    async def list_pending_for_sync(self, limit: int) -> list[PaymentRecord]:
        """Возвращает pending-платежи для опроса в ЮKassa."""


class SubscriptionRepository(ABC):
    @abstractmethod
    async def list_plans(self) -> list[SubscriptionPlan]:
        """Возвращает все тарифные планы."""

    @abstractmethod
    async def get_plan(self, plan_id: SubscriptionPlanId) -> SubscriptionPlan | None:
        """Возвращает тариф по идентификатору."""

    @abstractmethod
    async def get_active(self, user_id: UUID) -> UserSubscription | None:
        """Возвращает текущую подписку пользователя-тутора."""

    @abstractmethod
    async def upsert_active(self, subscription: UserSubscription) -> None:
        """Создаёт или обновляет текущую подписку."""

    @abstractmethod
    async def set_status(
        self,
        user_id: UUID,
        status: SubscriptionStatus,
    ) -> None:
        """Обновляет статус текущей подписки."""

    @abstractmethod
    async def append_history(self, period: SubscriptionPeriodHistory) -> None:
        """Добавляет запись в историю периодов."""

    @abstractmethod
    async def history_exists_for_payment(self, payment_id: UUID) -> bool:
        """Проверяет, есть ли история для платежа."""

    @abstractmethod
    async def list_history(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SubscriptionPeriodHistory]:
        """Возвращает историю периодов с данными платежа."""

    @abstractmethod
    async def list_due_for_renewal(self, limit: int) -> list[UserSubscription]:
        """Подписки с истёкшим периодом и согласием на автоплатеж."""

    @abstractmethod
    async def list_expired_without_autopayment(
        self, limit: int
    ) -> list[UserSubscription]:
        """Подписки с истёкшим периодом без автоплатежа."""


@dataclass
class CheckoutResult:
    payment_id: UUID
    confirmation_url: str | None


@dataclass
class UpgradeQuote:
    amount_rub: int
    requires_payment: bool
    period_start: datetime
    period_end: datetime
