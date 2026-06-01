"""JWT access middleware: карта ENDPOINT_ACCESS_RULES и роли."""

from uuid import UUID

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from api.access_policy import ENDPOINT_ACCESS_RULES
from auth.context import AuthContext
from auth.errors import AccessDeniedError
from auth.jwt import ACCESS_TOKEN_TYPE
from auth.models import UserRole


class JwtAccessMiddleware(BaseHTTPMiddleware):
    """Проверяет Bearer access JWT и роль по карте маршрутов."""

    def __init__(self, app, jwt_secret: str) -> None:
        super().__init__(app)
        self._jwt_secret = jwt_secret

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        route_path = self._resolve_route_path(request)
        rule = (
            ENDPOINT_ACCESS_RULES.get((request.method.upper(), route_path))
            if route_path is not None
            else None
        )
        if rule is None:
            return await call_next(request)
        if not rule.require_jwt:
            return await call_next(request)

        try:
            context = self._build_context(request)
            if rule.role is not None and context.role != rule.role:
                raise AccessDeniedError("Forbidden.")
        except AccessDeniedError as error:
            return JSONResponse(
                status_code=403,
                content={"code": error.code, "message": error.message},
            )

        request.state.auth_context = context
        request.state.user_id = context.user_id
        return await call_next(request)

    def _resolve_route_path(self, request: Request) -> str | None:
        for route in request.app.router.routes:
            if not isinstance(route, APIRoute):
                continue
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
        return None

    def _build_context(self, request: Request) -> AuthContext:
        header_value = request.headers.get("Authorization")
        if header_value is None or not header_value.startswith("Bearer "):
            raise AccessDeniedError("JWT token is required.")
        token = header_value[len("Bearer ") :].strip()
        if not token:
            raise AccessDeniedError("JWT token is required.")
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as error:
            raise AccessDeniedError("Invalid token.") from error
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise AccessDeniedError("Access token required.")
        role_value = payload.get("role")
        user_id_value = payload.get("sub")
        if role_value is None or user_id_value is None:
            raise AccessDeniedError("Invalid token payload.")
        return AuthContext(
            user_id=UUID(str(user_id_value)),
            role=UserRole(str(role_value)),
        )
