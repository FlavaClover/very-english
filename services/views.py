import logging
from abc import ABC, abstractmethod
from uuid import UUID

from auth.users import Users
from core.exceptions import TutorNotFoundError
from core.models import TutorProfile, TutorStatus
from core.tutors import TutorFilter
from core.views import TutorProfileViewAnalytics, TutorProfileViews

logger = logging.getLogger(__name__)


class AbstractTutorProfileViewService(ABC):
    """Прикладная логика учёта и выдачи недавних просмотров."""

    @abstractmethod
    async def record_view(self, user_id: UUID, tutor_id: UUID) -> None:
        """Фиксирует просмотр одобренного профиля тутора.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор тутора.
        """

    @abstractmethod
    async def list_recent_profiles(
        self,
        user_id: UUID,
        limit: int = 3,
    ) -> list[TutorProfile]:
        """Возвращает последние просмотренные одобренные профили.

        :param user_id: Идентификатор пользователя.
        :param limit: Сколько профилей вернуть.
        :return: Профили туторов в порядке последнего просмотра.
        """

    @abstractmethod
    async def remove_recent_view(self, user_id: UUID, tutor_id: UUID) -> None:
        """Удаляет конкретный просмотр из списка недавних.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор тутора.
        """

    @abstractmethod
    async def clear_recent_views(self, user_id: UUID) -> None:
        """Очищает весь список недавних просмотров пользователя.

        :param user_id: Идентификатор пользователя.
        """


class TutorProfileViewService(AbstractTutorProfileViewService):
    def __init__(
        self,
        views: TutorProfileViews,
        view_analytics: TutorProfileViewAnalytics,
        tutor_filter: TutorFilter,
        users: Users,
    ) -> None:
        self._views = views
        self._view_analytics = view_analytics
        self._tutor_filter = tutor_filter
        self._users = users

    async def record_view(self, user_id: UUID, tutor_id: UUID) -> None:
        own_tutor_id = await self._users.get_tutor_id(user_id)
        if own_tutor_id == tutor_id:
            return

        try:
            profile = await self._tutor_filter.get(tutor_id)
        except TutorNotFoundError:
            return

        if profile.status is not TutorStatus.APPROVED:
            return

        await self._views.upsert_view(user_id, tutor_id)
        await self._view_analytics.record_event(user_id, tutor_id)
        logger.info(
            "Зафиксирован просмотр профиля: user_id=%s tutor_id=%s",
            user_id,
            tutor_id,
        )

    async def list_recent_profiles(
        self,
        user_id: UUID,
        limit: int = 3,
    ) -> list[TutorProfile]:
        recent_views = await self._views.list_recent(user_id, limit)
        profiles: list[TutorProfile] = []
        for view in recent_views:
            try:
                profile = await self._tutor_filter.get(view.tutor_id)
            except TutorNotFoundError:
                continue
            if profile.status is not TutorStatus.APPROVED:
                continue
            profiles.append(profile)
        return profiles

    async def remove_recent_view(self, user_id: UUID, tutor_id: UUID) -> None:
        await self._views.delete_view(user_id, tutor_id)
        logger.info(
            "Удалён просмотр из недавних: user_id=%s tutor_id=%s",
            user_id,
            tutor_id,
        )

    async def clear_recent_views(self, user_id: UUID) -> None:
        await self._views.delete_all(user_id)
        logger.info(
            "Очищен список недавних просмотров: user_id=%s",
            user_id,
        )
