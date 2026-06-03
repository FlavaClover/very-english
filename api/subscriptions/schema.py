from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class SubscriptionPlanResponse(BaseModel):
    id: str
    price_rub: int
    billing_interval: str


class UserSubscriptionResponse(BaseModel):
    user_id: UUID
    plan_id: str
    status: str
    period_start: datetime
    period_end: datetime
    paid_at: datetime
    yookassa_payment_method_id: str | None = None


class SubscriptionHistoryItemResponse(BaseModel):
    id: UUID
    payment_id: UUID
    plan_id: str
    event_type: str
    period_start: datetime
    period_end: datetime
    paid_at: datetime
    amount_rub: int | None = None
    payment_status: str | None = None


class PaymentResponse(BaseModel):
    id: UUID
    plan_id: str
    event_type: str
    amount_rub: int
    status: str
    yookassa_payment_id: str | None = None
    paid_at: datetime | None = None
    created_at: datetime | None = None


class CheckoutRequest(BaseModel):
    plan_id: str = Field(min_length=1)
    return_url: HttpUrl


class UpgradeRequest(BaseModel):
    return_url: HttpUrl


class UpgradeQuoteResponse(BaseModel):
    amount_rub: int
    requires_payment: bool
    period_start: datetime
    period_end: datetime


class CheckoutResponse(BaseModel):
    payment_id: UUID
    confirmation_url: str | None = None
