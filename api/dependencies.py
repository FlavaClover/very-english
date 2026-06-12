from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from auth.jwt import JwtIssuer
from auth.passwords import BcryptPasswordHasher, PasswordHasher
from auth.users import AbstractUserManager, UserManager, Users
from auth.vkid import VkIdOAuth
from billing.yookassa_client import YooKassaClient
from services.subscription import AbstractSubscriptionService, SubscriptionService
from services.views import AbstractTutorProfileViewService, TutorProfileViewService
from infra.payments import PaymentsPg
from infra.email_verification import (
    EmailVerificationsPg,
    RedisEmailQueue,
    VerificationCodeHasher,
)
from infra.users import UsersPg
from core.tutors import Media, TutorFilter
from services.tags import AbstractTagsManager, TagsManager
from services.tutors import AbstractTutorManager, TutorManager
from infra.achievements import AchievementsPg
from infra.advantages import AdvantagesPg
from infra.contacts import ContactsPg
from infra.tags import TagsPg
from infra.subscriptions import SubscriptionsPg
from infra.tutor_filter import TutorFilterPg
from infra.views import TutorProfileViewAnalyticsPg, TutorProfileViewsPg
from infra.tutors import TutorsPg
from auth.email_verification import AbstractEmailVerificationService
from services.email_verification import EmailVerificationService, RandomCodeGenerator

MEDIA_URL_CACHE_TTL_SECONDS = 3600


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    """Открывает транзакцию на время HTTP-запроса."""
    engine: AsyncEngine = request.app.state.db_engine
    async with engine.begin() as conn:
        yield conn


def get_jwt_issuer(request: Request) -> JwtIssuer:
    return request.app.state.jwt_issuer


def get_vkid_oauth(request: Request) -> VkIdOAuth:
    return request.app.state.vkid_client


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
    vkid_oauth: VkIdOAuth,
    email_verification_service: AbstractEmailVerificationService,
) -> UserManager:
    return UserManager(
        users=UsersPg(conn),
        media=media,
        password_hasher=password_hasher,
        jwt_issuer=jwt_issuer,
        vkid_oauth=vkid_oauth,
        email_verification_service=email_verification_service,
    )


def build_email_verification_service(
    conn: AsyncConnection,
    users: Users,
    request: Request,
) -> EmailVerificationService:
    test_queue = getattr(request.app.state, "test_email_queue", None)
    if test_queue is None:
        test_queue = RedisEmailQueue(
            client=request.app.state.redis,
            queue_key=request.app.state.email_queue_key,
        )
    code_generator = getattr(
        request.app.state,
        "email_code_generator",
        None,
    )
    if code_generator is None:
        code_generator = RandomCodeGenerator(
            length=request.app.state.email_otp_code_length,
        )
    return EmailVerificationService(
        verifications=EmailVerificationsPg(conn),
        users=users,
        queue=test_queue,
        code_hasher=VerificationCodeHasher(request.app.state.email_code_pepper),
        code_generator=code_generator,
        code_ttl_seconds=request.app.state.email_code_ttl_seconds,
        verification_ttl_seconds=request.app.state.email_verification_ttl_seconds,
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


async def get_users(
    conn: AsyncConnection = Depends(get_connection),
) -> Users:
    return UsersPg(conn)


async def get_email_verification_service(
    request: Request,
    conn: AsyncConnection = Depends(get_connection),
    users: Users = Depends(get_users),
) -> AbstractEmailVerificationService:
    return build_email_verification_service(conn, users, request)


async def get_user_manager(
    conn: AsyncConnection = Depends(get_connection),
    media: Media = Depends(get_media),
    jwt_issuer: JwtIssuer = Depends(get_jwt_issuer),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    vkid_oauth: VkIdOAuth = Depends(get_vkid_oauth),
    email_verification_service: AbstractEmailVerificationService = Depends(),
) -> AbstractUserManager:
    return build_user_manager(
        conn,
        media,
        jwt_issuer,
        password_hasher,
        vkid_oauth,
        email_verification_service,
    )


async def get_tutor_filter(
    conn: AsyncConnection = Depends(get_connection),
) -> TutorFilter:
    return TutorFilterPg(conn)


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


async def get_view_service(
    conn: AsyncConnection = Depends(get_connection),
) -> AbstractTutorProfileViewService:
    return TutorProfileViewService(
        views=TutorProfileViewsPg(conn),
        view_analytics=TutorProfileViewAnalyticsPg(conn),
        tutor_filter=TutorFilterPg(conn),
        users=UsersPg(conn),
    )
