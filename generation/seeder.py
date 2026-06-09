import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth.models import UserRole
from auth.passwords import BcryptPasswordHasher
from core.models import Achievement, Advantage, Point
from billing.subscriptions import (
    SubscriptionPlanId,
    SubscriptionStatus,
    UserSubscription,
)
from generation.config import GenerationConfig
from generation.fixtures import ProfileFixtures
from generation.media_storage import GenerationMediaStorage
from generation.proxy import mask_proxy_url
from generation.remote_media import RemoteMediaFetcher
from infra.achievements import AchievementsPg
from infra.advantages import AdvantagesPg
from infra.contacts import ContactsPg
from infra.subscriptions import SubscriptionsPg
from infra.tags import TagsPg
from infra.tutors import TutorsPg
from infra.users import UsersPg

logger = logging.getLogger(__name__)


@dataclass
class GeneratedAccount:
    """Строка отчёта о созданном аккаунте."""

    full_name: str
    role: str
    subscription: str
    tutor_status: str
    login: str
    password: str


class DatabaseSeeder:
    """Наполняет БД тегами, пользователями и туторами."""

    def __init__(
        self,
        connection: AsyncConnection,
        fixtures: ProfileFixtures,
        media_storage: GenerationMediaStorage,
        password_hasher: BcryptPasswordHasher,
    ) -> None:
        self._connection = connection
        self._fixtures = fixtures
        self._media = media_storage
        self._password_hasher = password_hasher
        self._accounts: list[GeneratedAccount] = []

    @property
    def accounts(self) -> list[GeneratedAccount]:
        return list(self._accounts)

    async def run(
        self,
        tag_count: int,
        user_count: int,
        tutors_base: int,
        tutors_pro: int,
    ) -> list[GeneratedAccount]:
        """Выполняет полный цикл генерации.

        :param tag_count: Число тегов.
        :param user_count: Число обычных пользователей.
        :param tutors_base: Число туторов с подпиской BASE.
        :param tutors_pro: Число туторов с подпиской PRO.
        :return: Список созданных аккаунтов для отчёта.
        :raises RuntimeError: Вызов вне активной транзакции БД.
        """
        self._require_active_transaction()
        logger.info("Старт генерации данных (все INSERT/UPDATE в текущей транзакции)")
        await self._ensure_subscription_plans()
        tag_pool = await self._seed_tags(tag_count)
        users = UsersPg(self._connection)

        if user_count:
            logger.info("Этап: обычные пользователи (%s шт.)", user_count)
        for index in range(user_count):
            await self._create_regular_user(users, index, user_count)

        tutor_index = 0
        if tutors_base:
            logger.info("Этап: туторы BASE (%s шт.)", tutors_base)
        for slot in range(tutors_base):
            await self._create_tutor(
                users=users,
                tag_pool=tag_pool,
                plan=SubscriptionPlanId.BASE,
                with_advantage=False,
                status_index=tutor_index,
                slot=slot + 1,
                total=tutors_base,
            )
            tutor_index += 1

        if tutors_pro:
            logger.info("Этап: туторы PRO (%s шт.)", tutors_pro)
        for slot in range(tutors_pro):
            await self._create_tutor(
                users=users,
                tag_pool=tag_pool,
                plan=SubscriptionPlanId.PRO,
                with_advantage=True,
                status_index=tutor_index,
                slot=slot + 1,
                total=tutors_pro,
            )
            tutor_index += 1

        logger.info(
            "Готово: тегов=%s, пользователей=%s, туторов BASE=%s, PRO=%s, "
            "аккаунтов в отчёте=%s",
            len(tag_pool),
            user_count,
            tutors_base,
            tutors_pro,
            len(self.accounts),
        )
        return self.accounts

    def _require_active_transaction(self) -> None:
        if not self._connection.in_transaction():
            raise RuntimeError(
                "DatabaseSeeder должен работать внутри единой транзакции; "
                "используйте engine.begin() в GenerationRunner"
            )

    async def _ensure_subscription_plans(self) -> None:
        logger.info("Проверка тарифов подписок (base/pro)")
        await self._connection.execute(
            text(
                """
                INSERT INTO subscription_plans (id, price_rub, billing_interval)
                VALUES
                    ('base', 990, 'month'),
                    ('pro', 1990, 'month')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )

    async def _seed_tags(self, count: int) -> list[str]:
        logger.info("Этап: теги (%s шт.)", count)
        tags = TagsPg(self._connection)
        names: list[str] = []
        while len(names) < count:
            name = self._fixtures.tag_name()
            if name in names:
                logger.debug("Пропуск дубликата тега: %s", name)
                continue
            await tags.add(name)
            names.append(name)
            logger.info("[%s/%s] Тег: %s", len(names), count, name)
        return names

    async def _create_regular_user(
        self,
        users: UsersPg,
        index: int,
        total: int,
    ) -> None:
        user, password = self._fixtures.build_user(
            role=UserRole.USER,
            email_prefix="user",
        )
        logger.info(
            "[%s/%s] Пользователь: %s %s (%s)",
            index + 1,
            total,
            user.first_name,
            user.last_name,
            user.email,
        )
        photo_key = await self._media.upload_user_photo(user.id)
        user.photo = photo_key
        await users.create(user, self._password_hasher.hash(password))
        logger.info("[%s/%s] Пользователь сохранён: id=%s", index + 1, total, user.id)
        self._accounts.append(
            GeneratedAccount(
                full_name=f"{user.first_name} {user.last_name}",
                role=UserRole.USER.value,
                subscription="—",
                tutor_status="—",
                login=user.email,
                password=password,
            )
        )

    async def _create_tutor(
        self,
        users: UsersPg,
        tag_pool: list[str],
        plan: SubscriptionPlanId,
        with_advantage: bool,
        status_index: int,
        slot: int,
        total: int,
    ) -> None:
        user, password = self._fixtures.build_user(
            role=UserRole.TUTOR,
            email_prefix=f"tutor-{plan.value}",
        )
        logger.info(
            "[%s/%s] Тутор %s: %s %s (%s)",
            slot,
            total,
            plan.value.upper(),
            user.first_name,
            user.last_name,
            user.email,
        )
        photo_key = await self._media.upload_user_photo(user.id)
        user.photo = photo_key
        await users.create(user, self._password_hasher.hash(password))

        tutor = self._fixtures.build_tutor()
        tutors = TutorsPg(self._connection)
        await tutors.create(tutor)
        status = self._fixtures.tutor_status(status_index)
        await tutors.set_status(tutor.id, status)
        await users.link_tutor(user.id, tutor.id)
        logger.info(
            "[%s/%s] Анкета тутора: id=%s, статус=%s, цена=%s, города=%s",
            slot,
            total,
            tutor.id,
            status.value,
            tutor.price,
            ", ".join(tutor.cities),
        )

        contacts_pg = ContactsPg(self._connection)
        contacts = self._fixtures.build_contacts()
        for contact in contacts:
            await contacts_pg.add(tutor.id, contact)
        logger.info(
            "[%s/%s] Контакты (%s): %s",
            slot,
            total,
            len(contacts),
            ", ".join(c.name for c in contacts),
        )

        tags_pg = TagsPg(self._connection)
        selected_tags = self._fixtures.pick_tags(tag_pool)
        for tag_name in selected_tags:
            await tags_pg.link_tag_to_tutor(tutor.id, tag_name)
        logger.info("[%s/%s] Теги профиля: %s", slot, total, ", ".join(selected_tags))

        achievements_pg = AchievementsPg(self._connection)
        achievement_count = random.randint(1, 3)
        logger.info("[%s/%s] Достижения: %s шт.", slot, total, achievement_count)
        for achievement_index in range(achievement_count):
            image_key = await self._media.upload_achievement_image(
                tutor.id,
                achievement_index,
            )
            await achievements_pg.add(
                tutor.id,
                Achievement(image=image_key),
            )

        if with_advantage:
            advantages_pg = AdvantagesPg(self._connection)
            video_key = await self._media.upload_visit_video(tutor.id)
            point_count = random.randint(3, 5)
            points = [
                Point(text=self._fixtures.advantage_point()) for _ in range(point_count)
            ]
            await advantages_pg.add(
                tutor.id,
                Advantage(video=video_key, points=points),
            )
            logger.info(
                "[%s/%s] Преимущества PRO: видео + %s пунктов",
                slot,
                total,
                point_count,
            )

        await self._activate_subscription(user.id, plan, slot, total)

        self._accounts.append(
            GeneratedAccount(
                full_name=f"{user.first_name} {user.last_name}",
                role=UserRole.TUTOR.value,
                subscription=plan.value.upper(),
                tutor_status=status.value,
                login=user.email,
                password=password,
            )
        )

    async def _activate_subscription(
        self,
        user_id,
        plan: SubscriptionPlanId,
        slot: int,
        total: int,
    ) -> None:
        now = datetime.now(UTC)
        subscriptions = SubscriptionsPg(self._connection)
        logger.info(
            "[%s/%s] Подписка %s активирована до %s",
            slot,
            total,
            plan.value.upper(),
            (now + timedelta(days=30)).date(),
        )
        await subscriptions.upsert_active(
            UserSubscription(
                user_id=user_id,
                plan_id=plan,
                status=SubscriptionStatus.ACTIVE,
                period_start=now,
                period_end=now + timedelta(days=30),
                paid_at=now,
                yookassa_payment_method_id=f"gen-{uuid4()}",
            )
        )


class GenerationRunner:
    """Запускает сидер в транзакции с HTTP-клиентом."""

    def __init__(self, config: GenerationConfig) -> None:
        self._config = config

    async def execute(
        self,
        tag_count: int,
        user_count: int,
        tutors_base: int,
        tutors_pro: int,
    ) -> list[GeneratedAccount]:
        from sqlalchemy.ext.asyncio import create_async_engine

        runner_logger = logging.getLogger(__name__)
        runner_logger.info("Подключение к БД")
        engine = create_async_engine(self._config.database_url, pool_pre_ping=True)
        password_hasher = BcryptPasswordHasher()
        fixtures = ProfileFixtures()

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=45)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            ) as http_session:
                if self._config.http_proxy:
                    runner_logger.info(
                        "HTTP-сессия для медиа (SSL off, прокси: %s)",
                        mask_proxy_url(self._config.http_proxy),
                    )
                else:
                    runner_logger.info(
                        "HTTP-сессия для загрузки медиа (проверка SSL отключена)"
                    )
                fetcher = RemoteMediaFetcher(
                    http_session,
                    proxy=self._config.http_proxy,
                )
                media_storage = GenerationMediaStorage.from_config(
                    fetcher=fetcher,
                    bucket=self._config.s3_bucket,
                    aws_access_key_id=self._config.aws_access_key_id,
                    aws_secret_access_key=self._config.aws_secret_access_key,
                    aws_region=self._config.aws_region,
                    aws_endpoint_url=self._config.aws_endpoint_url,
                    aws_public_endpoint_url=self._config.aws_public_endpoint_url,
                )
                try:
                    async with engine.begin() as connection:
                        runner_logger.info(
                            "Открыта единая транзакция БД: при любой ошибке — "
                            "полный rollback без частичных записей"
                        )
                        seeder = DatabaseSeeder(
                            connection=connection,
                            fixtures=fixtures,
                            media_storage=media_storage,
                            password_hasher=password_hasher,
                        )
                        accounts = await seeder.run(
                            tag_count=tag_count,
                            user_count=user_count,
                            tutors_base=tutors_base,
                            tutors_pro=tutors_pro,
                        )
                    runner_logger.info("Транзакция зафиксирована (commit)")
                    return accounts
                except Exception:
                    runner_logger.error(
                        "Генерация прервана: rollback транзакции БД, "
                        "частичные данные не сохранены"
                    )
                    raise
        finally:
            runner_logger.info("Закрытие подключения к БД")
            await engine.dispose()
