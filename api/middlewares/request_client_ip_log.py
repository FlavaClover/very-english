import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestClientIpLogMiddleware(BaseHTTPMiddleware):
    """Логирует входящий HTTP-запрос: маршрут и IP из proxy-заголовков."""

    async def dispatch(self, request: Request, call_next):
        client_host = None
        if request.client is not None:
            client_host = request.client.host

        logger.info(
            "HTTP request %s %s x_real_ip=%s x_forwarded_for=%s client_host=%s",
            request.method,
            request.url.path,
            request.headers.get("X-Real-IP", None),
            request.headers.get("X-Forwarded-For", None),
            client_host,
        )
        return await call_next(request)
