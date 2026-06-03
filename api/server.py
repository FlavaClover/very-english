import aiohttp
from contextlib import asynccontextmanager

import aioboto3
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import create_async_engine

from api.access_policy import ENDPOINT_ACCESS_RULES
from api.admin.endpoints import router as admin_router
from api.auth.endpoints import router as auth_router
from api.billing.webhook import router as billing_router
from api.catalog.endpoints import router as catalog_router
from api.dependencies import (
    MEDIA_URL_CACHE_TTL_SECONDS,
    get_media,
    get_subscription_service,
    get_tags_manager,
    get_tutor_filter,
    get_tutor_manager,
    get_user_manager,
    get_users,
)
from api.middlewares import JwtAccessMiddleware, SubscriptionAccessMiddleware
from api.middlewares.request_client_ip_log import RequestClientIpLogMiddleware
from api.middlewares.yookassa_webhook_ip import YooKassaWebhookIpMiddleware
from api.subscriptions.endpoints import router as subscriptions_router
from api.tags.endpoints import router as tags_router
from api.tutors.endpoints import router as tutors_router
from api.users.endpoints import router as users_router
from auth.jwt import JwtIssuer
from auth.users import AbstractUserManager, Users
from billing.yookassa_client import YooKassaClient
from billing.yookassa_webhook_ip import YooKassaWebhookIpValidator
from core.subscriptions import AbstractSubscriptionService
from core.tutors import AbstractTagsManager, AbstractTutorManager, Media, TutorFilter
from infra.s3_media import S3Media


def create_server(
    database_url: str,
    jwt_secret_key: str,
    cors_allow_origins: list[str],
    s3_bucket: str,
    yookassa_shop_id: str,
    yookassa_secret_key: str,
    jwt_expire_minutes: int = 60,
    jwt_refresh_expire_days: int = 7,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_region: str = "us-east-1",
    aws_endpoint_url: str | None = None,
    aws_public_endpoint_url: str | None = None,
    redis_url: str = "redis://127.0.0.1:6379/0",
    yookassa_webhook_ip_check_enabled: bool = True,
) -> FastAPI:
    """Собирает FastAPI-приложение с DI, middleware и роутерами."""
    db_engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http_session = aiohttp.ClientSession()
        app.state.yookassa_http_session = http_session
        app.state.yookassa_client = YooKassaClient(
            http_session,
            yookassa_shop_id,
            yookassa_secret_key,
        )
        yield
        await http_session.close()
        await db_engine.dispose()

    app = FastAPI(title="Very English API", version="0.1.0", lifespan=lifespan)

    app.state.db_engine = db_engine
    app.state.cors_allow_origins = cors_allow_origins
    app.state.yookassa_webhook_ip_validator = YooKassaWebhookIpValidator(
        enabled=yookassa_webhook_ip_check_enabled,
    )
    app.state.jwt_issuer = JwtIssuer(
        secret_key=jwt_secret_key,
        expire_minutes=jwt_expire_minutes,
        refresh_expire_days=jwt_refresh_expire_days,
    )
    app.state.s3_bucket = s3_bucket
    session_kwargs: dict = {"region_name": aws_region}
    if aws_access_key_id and aws_secret_access_key:
        session_kwargs["aws_access_key_id"] = aws_access_key_id
        session_kwargs["aws_secret_access_key"] = aws_secret_access_key
    app.state.s3_session = aioboto3.Session(**session_kwargs)
    app.state.aws_endpoint_url = aws_endpoint_url
    app.state.aws_public_endpoint_url = aws_public_endpoint_url
    app.state.redis = redis.from_url(redis_url, decode_responses=True)
    app.state.media = S3Media(
        session=app.state.s3_session,
        bucket=s3_bucket,
        endpoint_url=aws_endpoint_url,
        public_endpoint_url=aws_public_endpoint_url,
        presigned_expire_seconds=MEDIA_URL_CACHE_TTL_SECONDS,
        redis_client=app.state.redis,
        url_cache_ttl_seconds=MEDIA_URL_CACHE_TTL_SECONDS,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(SubscriptionAccessMiddleware, db_engine=db_engine)
    app.add_middleware(JwtAccessMiddleware, jwt_secret=jwt_secret_key)
    app.add_middleware(YooKassaWebhookIpMiddleware)
    app.add_middleware(RequestClientIpLogMiddleware)

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(tags_router)
    app.include_router(catalog_router)
    app.include_router(tutors_router)
    app.include_router(admin_router)
    app.include_router(subscriptions_router)
    app.include_router(billing_router)

    app.dependency_overrides[Media] = get_media
    app.dependency_overrides[Users] = get_users
    app.dependency_overrides[AbstractUserManager] = get_user_manager
    app.dependency_overrides[AbstractTutorManager] = get_tutor_manager
    app.dependency_overrides[AbstractTagsManager] = get_tags_manager
    app.dependency_overrides[TutorFilter] = get_tutor_filter
    app.dependency_overrides[AbstractSubscriptionService] = get_subscription_service

    def custom_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Access token as Bearer JWT.",
        }
        paths = schema.get("paths", {})
        for path, operations in paths.items():
            for method, operation in operations.items():
                rule = ENDPOINT_ACCESS_RULES.get((method.upper(), path))
                if rule is not None and rule.require_jwt:
                    operation["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app
