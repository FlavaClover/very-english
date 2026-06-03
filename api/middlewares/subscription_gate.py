from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import BaseHTTPMiddleware

from api.access_policy import RequiredSubscription
from api.middlewares.route_access import resolve_endpoint_access_rule
from auth.errors import AccessDeniedError
from billing.subscriptions import SubscriptionPlanId, SubscriptionStatus
from infra.subscriptions import SubscriptionsPg


class ProPlanRequiredError(AccessDeniedError):
    code = "pro_plan_required"


class SubscriptionRequiredError(AccessDeniedError):
    code = "subscription_required"


class SubscriptionAccessMiddleware(BaseHTTPMiddleware):
    """Проверяет подписку пользователя-тутора после JwtAccessMiddleware."""

    def __init__(self, app, db_engine: AsyncEngine) -> None:
        super().__init__(app)
        self._db_engine = db_engine

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        rule = resolve_endpoint_access_rule(request)
        if rule is None or rule.required_subscription is None:
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            return JSONResponse(
                status_code=403,
                content={
                    "code": "access_denied",
                    "message": "JWT token is required.",
                },
            )

        try:
            async with self._db_engine.begin() as connection:
                await self._enforce(
                    connection,
                    user_id,
                    rule.required_subscription,
                )
        except AccessDeniedError as error:
            return JSONResponse(
                status_code=403,
                content={"code": error.code, "message": error.message},
            )

        return await call_next(request)

    async def _enforce(
        self,
        connection,
        user_id: UUID,
        required: RequiredSubscription,
    ) -> None:
        subscriptions = SubscriptionsPg(connection)
        active = await subscriptions.get_active(user_id)
        if active is None or active.status is not SubscriptionStatus.ACTIVE:
            raise SubscriptionRequiredError("Active subscription required.")

        if required is RequiredSubscription.PRO:
            if active.plan_id is not SubscriptionPlanId.PRO:
                raise ProPlanRequiredError("PRO subscription required.")
            return

        if active.plan_id not in {
            SubscriptionPlanId.BASE,
            SubscriptionPlanId.PRO,
        }:
            raise SubscriptionRequiredError("Active subscription required.")
