from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.return_url import validate_return_url
from api.schema import ErrorResponse
from api.subscriptions.schema import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentResponse,
    SubscriptionHistoryItemResponse,
    SubscriptionPlanResponse,
    UpgradeQuoteResponse,
    UpgradeRequest,
    UserSubscriptionResponse,
)
from core.subscriptions import AbstractSubscriptionService, SubscriptionPlanId
from services.subscription_service import (
    InvalidPlanError,
    InvalidSubscriptionStateError,
    SubscriptionNotFoundError,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def _parse_plan_id(raw: str) -> SubscriptionPlanId:
    try:
        return SubscriptionPlanId(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_plan_id") from exc


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanResponse],
    summary="Список тарифных планов",
)
async def list_plans(
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> list[SubscriptionPlanResponse]:
    plans = await subscription_service.list_plans()
    return [
        SubscriptionPlanResponse(
            id=plan.id.value,
            price_rub=plan.price_rub,
            billing_interval=plan.billing_interval,
        )
        for plan in plans
    ]


@router.get(
    "/me",
    response_model=UserSubscriptionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Текущая подписка тутора",
)
async def get_my_subscription(
    request: Request,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> UserSubscriptionResponse | Response:
    subscription = await subscription_service.get_active_subscription(
        request.state.user_id,
    )
    if subscription is None:
        return Response(
            content=ErrorResponse(detail="Subscription not found").model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return UserSubscriptionResponse(
        user_id=subscription.user_id,
        plan_id=subscription.plan_id.value,
        status=subscription.status.value,
        period_start=subscription.period_start,
        period_end=subscription.period_end,
        paid_at=subscription.paid_at,
        yookassa_payment_method_id=subscription.yookassa_payment_method_id,
    )


@router.get(
    "/me/history",
    response_model=list[SubscriptionHistoryItemResponse],
    summary="История периодов подписки",
)
async def get_my_history(
    request: Request,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
    limit: int = 50,
    offset: int = 0,
) -> list[SubscriptionHistoryItemResponse]:
    history = await subscription_service.list_history(
        request.state.user_id,
        limit,
        offset,
    )
    return [
        SubscriptionHistoryItemResponse(
            id=item.id,
            payment_id=item.payment_id,
            plan_id=item.plan_id.value,
            event_type=item.event_type.value,
            period_start=item.period_start,
            period_end=item.period_end,
            paid_at=item.paid_at,
            amount_rub=item.amount_rub,
            payment_status=(item.payment_status.value if item.payment_status else None),
        )
        for item in history
    ]


@router.get(
    "/me/payments",
    response_model=list[PaymentResponse],
    summary="История платежей тутора",
)
async def get_my_payments(
    request: Request,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
    limit: int = 50,
    offset: int = 0,
) -> list[PaymentResponse]:
    payments = await subscription_service.list_payments(
        request.state.user_id,
        limit,
        offset,
    )
    return [
        PaymentResponse(
            id=payment.id,
            plan_id=payment.plan_id.value,
            event_type=payment.event_type.value,
            amount_rub=payment.amount_rub,
            status=payment.status.value,
            yookassa_payment_id=payment.yookassa_payment_id,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
        )
        for payment in payments
    ]


@router.get(
    "/me/upgrade/quote",
    response_model=UpgradeQuoteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Сумма доплаты за апгрейд BASE → PRO",
)
async def get_upgrade_quote(
    request: Request,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> UpgradeQuoteResponse | Response:
    try:
        quote = await subscription_service.get_upgrade_quote(request.state.user_id)
    except SubscriptionNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    except InvalidSubscriptionStateError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except InvalidPlanError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )

    return UpgradeQuoteResponse(
        amount_rub=quote.amount_rub,
        requires_payment=quote.requires_payment,
        period_start=quote.period_start,
        period_end=quote.period_end,
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Оформление подписки",
)
async def checkout(
    request: Request,
    payload: CheckoutRequest,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> CheckoutResponse | Response:
    try:
        validate_return_url(
            str(payload.return_url),
            request.app.state.cors_allow_origins,
        )
        plan_id = _parse_plan_id(payload.plan_id)
        result = await subscription_service.checkout(
            user_id=request.state.user_id,
            plan_id=plan_id,
            return_url=str(payload.return_url),
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except InvalidPlanError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except InvalidSubscriptionStateError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )

    return CheckoutResponse(
        payment_id=result.payment_id,
        confirmation_url=result.confirmation_url,
    )


@router.post(
    "/upgrade",
    response_model=CheckoutResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Апгрейд BASE → PRO",
)
async def upgrade(
    request: Request,
    payload: UpgradeRequest,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> CheckoutResponse | Response:
    try:
        validate_return_url(
            str(payload.return_url),
            request.app.state.cors_allow_origins,
        )
        result = await subscription_service.upgrade(
            user_id=request.state.user_id,
            return_url=str(payload.return_url),
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except SubscriptionNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    except InvalidSubscriptionStateError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )

    return CheckoutResponse(
        payment_id=result.payment_id,
        confirmation_url=result.confirmation_url,
    )
