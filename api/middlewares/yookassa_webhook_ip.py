from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.schema import ErrorResponse
from billing.yookassa_webhook_ip import (
    YooKassaWebhookForbiddenError,
    YooKassaWebhookIpValidator,
)

YOOKASSA_WEBHOOK_PATH = "/billing/webhooks/yookassa"


class YooKassaWebhookIpMiddleware(BaseHTTPMiddleware):
    """Отклоняет webhook ЮKassa с IP вне официального списка."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path == YOOKASSA_WEBHOOK_PATH:
            validator: YooKassaWebhookIpValidator = (
                request.app.state.yookassa_webhook_ip_validator
            )
            try:
                validator.enforce(request)
            except YooKassaWebhookForbiddenError as error:
                return JSONResponse(
                    status_code=403,
                    content=ErrorResponse(detail=str(error)).model_dump(),
                )
        return await call_next(request)
