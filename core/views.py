from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class TutorProfileView:
    """Запись о просмотре профиля тутора."""

    tutor_id: UUID
    viewed_at: datetime


class TutorProfileViews(ABC):
    """Хранилище недавних просмотров профилей туторов для пользователя."""

    @abstractmethod
    async def upsert_view(self, user_id: UUID, tutor_id: UUID) -> None:
        """Сохраняет или обновляет время последнего просмотра.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор тутора.
        """

    @abstractmethod
    async def list_recent(
        self,
        user_id: UUID,
        limit: int,
    ) -> list[TutorProfileView]:
        """Возвращает последние просмотры, от новых к старым.

        :param user_id: Идентификатор пользователя.
        :param limit: Максимум записей.
        :return: Список просмотров.
        """

    @abstractmethod
    async def delete_view(self, user_id: UUID, tutor_id: UUID) -> None:
        """Удаляет просмотр конкретного тутора из списка недавних.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор тутора.
        """

    @abstractmethod
    async def delete_all(self, user_id: UUID) -> None:
        """Очищает весь список недавних просмотров пользователя.

        :param user_id: Идентификатор пользователя.
        """


class TutorProfileViewAnalytics(ABC):
    """Хранилище событий просмотров профилей туторов для аналитики."""

    @abstractmethod
    async def record_event(self, user_id: UUID, tutor_id: UUID) -> None:
        """Добавляет одно событие просмотра.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор тутора.
        """
