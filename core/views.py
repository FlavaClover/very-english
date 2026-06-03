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
    """Хранилище просмотров профилей туторов."""

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
