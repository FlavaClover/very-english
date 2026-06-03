from typing import Annotated

from fastapi import APIRouter, Depends, Request

from core.subscriptions import AbstractSubscriptionService

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post(
    "/webhooks/yookassa",
    summary="Webhook уведомлений ЮKassa",
)
async def yookassa_webhook(
    request: Request,
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> dict[str, str]:
    payload = await request.json()
    await subscription_service.handle_webhook(payload)
    return {"status": "ok"}
