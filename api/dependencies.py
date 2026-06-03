from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from auth.jwt import JwtIssuer
from auth.passwords import BcryptPasswordHasher, PasswordHasher
from auth.users import AbstractUserManager, UserManager, Users
from billing.yookassa_client import YooKassaClient
from core.subscriptions import AbstractSubscriptionService
from infra.payments import PaymentsPg
from infra.users import UsersPg
from core.tutors import (
    AbstractTagsManager,
    AbstractTutorManager,
    Media,
    TutorFilter,
    TutorManager,
    TagsManager,
)
from infra.achievements import AchievementsPg
from infra.advantages import AdvantagesPg
from infra.contacts import ContactsPg
from infra.tags import TagsPg
from infra.subscriptions import SubscriptionsPg
from infra.tutor_filter import TutorFilterPg
from infra.tutors import TutorsPg
from services.subscription_service import SubscriptionService

MEDIA_URL_CACHE_TTL_SECONDS = 3600


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    """Открывает транзакцию на время HTTP-запроса."""
    engine: AsyncEngine = request.app.state.db_engine
    async with engine.begin() as conn:
        yield conn


def get_jwt_issuer(request: Request) -> JwtIssuer:
    return request.app.state.jwt_issuer


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_media(request: Request) -> Media:
    return request.app.state.media


def build_tutor_manager(conn: AsyncConnection, media: Media) -> TutorManager:
    return TutorManager(
        tutors=TutorsPg(conn),
        tags=TagsPg(conn),
        contacts=ContactsPg(conn),
        achievements=AchievementsPg(conn),
        advantages=AdvantagesPg(conn),
        media=media,
    )


def build_tags_manager(conn: AsyncConnection) -> TagsManager:
    return TagsManager(tags=TagsPg(conn))


def build_user_manager(
    conn: AsyncConnection,
    media: Media,
    jwt_issuer: JwtIssuer,
    password_hasher: PasswordHasher,
) -> UserManager:
    return UserManager(
        users=UsersPg(conn),
        media=media,
        password_hasher=password_hasher,
        jwt_issuer=jwt_issuer,
    )


async def get_tutor_manager(
    conn: AsyncConnection = Depends(get_connection),
    media: Media = Depends(get_media),
) -> AbstractTutorManager:
    return build_tutor_manager(conn, media)


async def get_tags_manager(
    conn: AsyncConnection = Depends(get_connection),
) -> AbstractTagsManager:
    return build_tags_manager(conn)


async def get_user_manager(
    conn: AsyncConnection = Depends(get_connection),
    media: Media = Depends(get_media),
    jwt_issuer: JwtIssuer = Depends(get_jwt_issuer),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> AbstractUserManager:
    return build_user_manager(conn, media, jwt_issuer, password_hasher)


async def get_tutor_filter(
    conn: AsyncConnection = Depends(get_connection),
) -> TutorFilter:
    return TutorFilterPg(conn)


async def get_users(
    conn: AsyncConnection = Depends(get_connection),
) -> Users:
    return UsersPg(conn)


def get_yookassa_client(request: Request) -> YooKassaClient:
    return request.app.state.yookassa_client


async def get_subscription_service(
    conn: AsyncConnection = Depends(get_connection),
    gateway: YooKassaClient = Depends(get_yookassa_client),
) -> AbstractSubscriptionService:
    return SubscriptionService(
        payments=PaymentsPg(conn),
        subscriptions=SubscriptionsPg(conn),
        gateway=gateway,
    )
